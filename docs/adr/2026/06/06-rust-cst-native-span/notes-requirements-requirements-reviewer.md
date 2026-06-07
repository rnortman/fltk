# Requirements review: Rust CST Native Span

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope: adversarial review of requirements.md against request.md + exploration.md +
notes-requirements-user.md. Did not read code.

## requirements-1 — Title/filename still says "Span"; framing risks re-narrowing

Section: title "Requirements: Rust CST — No Python-Object References" (good) but the ADR
directory/slug is `rust-cst-native-span` and the title was clearly edited from a span-only
framing.

What's wrong: The user's correction (notes-requirements-user.md) was emphatic that the
requirement is "with respect to *FUCKING ANYTHING*," not span. The doc body now reflects this
(Goals para; In scope bullets include `children`; "no Python-object reference, not an
enumerated list"). This is correctly fixed in the body. The residual risk is purely the
slug/title legacy — a downstream reader skimming the slug could re-narrow. Minor.

Consequence: A designer skimming the slug may under-scope to span again — the exact failure
the user flagged. Low risk given the body is explicit.

Suggested fix: None required to the body. Optionally note in the Goals that the ADR slug is
historical and the scope is all node-state fields. Leave as-is is acceptable.

## requirements-2 — `children` migration smuggled in as firm scope despite request naming only span; magnitude not surfaced to requester

Section: In scope — "`children: Py<PyList>` → a native Rust container…"; Open question
`children-container-shape`.

What's wrong: The request says "no Rust CST node may hold a reference to any Python object"
(broad) but explicitly identifies span: "The request explicitly names span." Exploration Open
question 4 flags children migration as "a potentially much larger change." The user correction
confirms the broad reading — so including children IS correct per the user. But the doc commits
to the full children-container redesign (native enum, traversal API, accessor re-sourcing) as
firm in-scope while the exploration warns this is potentially the largest part of the work, and
the request gave no signal the requester sized it. The doc does not flag to the requester that
this single requirement (children) likely dwarfs the span change in effort and reshapes the
public Rust traversal API.

Why: exploration line ~113 "Changing span to native Rust does not resolve the children
dependency" and line ~211 "This is a potentially much larger change." Request: broad rule but
"explicitly names span."

Consequence: The requester gets a much larger, API-reshaping project than the literal request
suggested, without an explicit "this is big — confirm?" checkpoint. Given the user correction
("FUCKING ANYTHING"), the user clearly wants it — but the effort/scope blast radius (new public
traversal API, per-node child enums, downstream ergonomics) should be called out so the
requester can stage it, not discover it mid-build.

Suggested fix: Add a one-line scope-magnitude note: children migration is the dominant,
API-shaping portion and reshapes the public Rust traversal surface; consider whether it should
be staged (span first, children second) or done atomically. Do not drop it from scope — the
user wants it — but make the size explicit and offer staging.

## requirements-3 — `native-span-start-end` open question defaults to (B), which breaks an unknown number of out-of-tree consumers; tension with CLAUDE.md drop-in goal

Section: Open question `native-span-start-end`, "Proposed default: (B)".

What's wrong: Default (B) keeps `.start`/`.end` off native Span and accepts that out-of-tree
code reading `.start`/`.end` breaks on Rust-backend adoption. CLAUDE.md states the Rust backend
must be a "near-drop-in replacement … must not be forced to edit their type annotations or call
sites wholesale." `node.span.start` is a call-site/attribute access, not just an import. Option
(A) (expose `.start`/`.end`) is the cheaper-for-consumers path and the only one consistent with
"near-drop-in"; the doc's own exploration notes `terminalsrc.Span` exposes `.start`/`.end` and
that omission on native Span is a design decision enforced by one test. Defaulting to the
consumer-breaking option, against the project's stated drop-in invariant, is the wrong default
to propose.

Why: CLAUDE.md "near-drop-in replacement … must not be forced to edit … call sites wholesale."
Requirements constraint line ~144-147 restates this. `.start`/`.end` access is a call site.

Consequence: If (B) is adopted, every out-of-tree consumer reading span extents must rewrite
call sites on Rust-backend adoption — contradicting the drop-in promise the doc itself lists as
a constraint. Reversing later is another breaking surface change.

Suggested fix: Flip the proposed default to (A), framed as preserving drop-in parity; note the
cost is widening the native Span API and removing one enforcing test. Let the requester
override to (B) if they value the closed Span API over drop-in parity. (This is a
requester-decision; the point is the proposed default contradicts a stated project invariant.)

## requirements-4 — `__repr__` content not pinned; possible behavioral-equivalence gap

Section: "Node and span equality" / generator covers "repr" (In scope bullet, exploration
mentions `_repr_method`).

What's wrong: The doc requires equality to move to native comparison and lists repr among
generator-emitted methods, but states no acceptance for repr output. If repr previously
interpolated the Python span object's repr (`terminalsrc.Span(...)`) and now interpolates the
native `fltk._native.Span` repr, node `repr()` string output changes observably. Behavioral
equivalence section enumerates `.text()`, `.kind`, predicates, accessors, equality — omits
repr. Whether repr is a tracked surface is left undecided.

Consequence: Cross-backend `repr()` divergence may surface in downstream snapshot tests or logs
without being an acknowledged, intended change — or designer over-invests pinning repr that
nobody cares about. Either way undecided.

Suggested fix: Add one line: repr is/ isn't a tracked equivalence surface; if tracked, state
the expected form; if not, explicitly exclude it.

## requirements-5 — Acceptance "grep finds no Python-object-typed state field" is a near-implementation/test-mechanics constraint, borderline

Section: System behavior → Native node state → "Acceptance: a grep / type audit … finds no
Python-object-typed state field."

What's wrong: Mostly fine (it's an observable property of generated output, legitimate for a
public-Rust-API requirement). The "grep" phrasing edges toward prescribing the verification
mechanism. Acceptable because the underlying property (no PyObject state field) is the genuine
observable requirement and the parenthetical correctly carves out permitted `#[pymethods]`
binding getters. Flag only so the designer reads it as "property to hold," not "write this grep."

Consequence: Negligible. Designer might treat a grep as the literal test; harmless.

Suggested fix: Optional — reword "grep / type audit" to "an audit of every CST node struct
confirms no Python-object-typed state field."

## requirements-6 — Protocol annotation change: "backend-agnostic types/unions" under-specified vs no-annotation-churn constraint

Section: In scope "Protocol annotations for affected fields made backend-agnostic"; User-visible
"Protocol class annotations for affected fields change to backend-agnostic types/unions";
Constraint "no annotation churn beyond the affected field types."

What's wrong: Exploration (line 83-87) notes the protocol annotates the concrete Python
`terminalsrc.Span`, and the Python generated CST matches. Changing the protocol annotation to a
union/agnostic type is a public-API surface change on the protocol that out-of-tree consumers
type-check against — it can force downstream annotation updates (the very churn CLAUDE.md
warns about) even for consumers staying on the Python backend, if their type checker now sees a
widened union. The doc asserts "no annotation churn beyond affected fields" but a widened
protocol union IS churn on the affected field's type, potentially visible to Python-backend-only
consumers. The interaction (does the protocol widening affect Python-backend-only consumers?)
is not resolved.

Why: CLAUDE.md "Changing the type-annotation surface in ways that force downstream callers to
update … is also a breaking change." Exploration line 84-85 "The protocol annotation is not
backend-agnostic — it names the concrete Python type."

Consequence: Designer may widen the protocol Span annotation in a way that breaks
Python-backend-only consumers' type checking — contradicting the out-of-scope promise that
Python-backend consumers "see no change."

Suggested fix: State explicitly whether the protocol annotation change is required to be a
strict superset that keeps existing Python-backend type-checks passing (additive union, not
replacement), and confirm Python-backend-only consumers see no type-check regression.

## requirements-7 — No findings on the core scope correction

The central risk (the user's "scoped down to span" complaint) is correctly addressed: Goals and
In scope both state the requirement is "no Python-object reference," explicitly list `children`,
and say "not an enumerated list." This matches the user correction. No finding — noting it so
the chain sees it was checked.

---

Notes: Concise/precise/complete/unambiguous; no padding. Audience smart LLM/human.
