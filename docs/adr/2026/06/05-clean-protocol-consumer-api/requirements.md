# Requirements: Clean Protocol-Only Consumer API

> Authoring note (applies to this doc): Concise. Precise. Complete. Unambiguous. No design, no file paths/function names, no test plan, no implementation steps. Acceptance criteria state *what is true*, not *how to verify mechanics*.

## Goals

An above-the-parser, **out-of-tree** consumer of FLTK-generated CST can write clean code importing ONLY the generated protocol module — no separate concrete-CST import, no type-vs-runtime dual binding, no CST-forced narrowing or suppressions — including narrowing a child-union element to its concrete node type within **any traversal pattern they themselves write**. The in-tree consumer `fltk2gsm.py` is the **model** user (one call site, not the spec) and is brought to this standard end-to-end by consuming the same general primitive.

## Gating criterion (HARD, verbatim)

> "A gating criteria is that user code (and fltk2gsm.py is a model for user code) must be *clean*. No double-importing, no TYPE_CHECKING hacks, no `cast`, no `noqa` or other pyright/ruff suppressions forced by the cst. This needs to carry through from requirements to design."

This is gating: every section below is constrained by it. A consumer is "clean" iff, against the FLTK-generated CST surface, it needs none of: a dual concrete+protocol import of the same logical name; a `TYPE_CHECKING`-guarded shadowing import of the CST module; a `typing.cast` forced by CST types; a `# noqa` / pyright / ruff suppression forced by the CST surface. Suppressions a consumer would need *independent of the CST* (e.g. a project's assert-in-non-test policy) are out of the CST's scope and not counted — see Out of scope.

**Substitution does not satisfy the criterion.** Trading a CST-forced `cast` for any other CST-forced suppression (`# type: ignore`, `# pyright: ignore`, `# noqa`) is not "eliminating" it — the result is still a CST-forced suppression and still fails this gate.

## Required consumer-code shapes (NORMATIVE — acceptance anchor)

These two exact shapes are the acceptance anchor. Any design or implementation that does not reproduce them **modulo identifier names FAILS**. Both import ONLY the generated protocol module. Both must be pyright-clean and ruff-clean with NO `cast`, NO `TYPE_CHECKING` shadow import, NO `@runtime_checkable`, NO CST-forced suppression of any kind. Backed empirically by `narrowing-mechanism-probe.md` (probe IDs cited inline).

Both shapes reference the discriminant ONLY as `cst.<Node>.kind` — the `NodeKind` / `SpanKind` enum *names* are NOT exposed in consumer code (probe D3/D4: nodes expose `<Node>.kind` as a Literal-typed class attribute; the enum namespace stays hidden).

### Shape 1 — structurally-known single type (the in-tree MODEL consumer, `fltk2gsm.visit_items`)

```python
from fltk.fegen import fltk_cst_protocol as cst   # single CST import

for (item_label, item), (sep_label, _) in zip(children[::2], children[1::2], strict=False):
    assert item.kind == cst.Item.kind          # narrows item: Item|Trivia|Span -> cst.Item; no cast, bare assert
    gsm_items.append(self.visit_item(item))
    ...
```

The `assert` is **bare** — no `# noqa: S101` (see Constraints: `S101` dropped from ruff selection). The discriminant comparison `item.kind == cst.Item.kind` performs the narrowing (probe D2: `if child.kind == Item.kind` narrows the outer `child`; probe A2: cross-enum Literal discriminants narrow even though `Span.kind` is a different enum).

### Shape 2 — general dispatch over a heterogeneous child union (the OUT-OF-TREE target use case)

```python
from fltk.fegen import fltk_cst_protocol as cst

for label, child in node.children:
    match child.kind:
        case cst.Item.kind:    handle_item(child)     # child narrowed to cst.Item
        case cst.Trivia.kind:  handle_trivia(child)   # child narrowed to cst.Trivia
        case cst.Span.kind:    handle_span(child)     # child narrowed to cst.Span
```

`case cst.<Node>.kind:` is a dotted-name VALUE pattern; pyright narrows the outer `child` per arm (probe D1/D3). `cst.Span.kind` narrows to `cst.Span` via the shared `SpanKind.SPAN` Literal (probe A2/D1).

These two shapes are **structurally different traversal patterns** (interleaved item/separator pairing vs. heterogeneous match/case dispatch) and together discharge the generality requirement (AC 11). Neither shape is, nor may be served by, a traversal-shaped accessor (see **Rejected approaches**).

## In scope

- The generated protocol module exposes, at runtime, the enum **values** a protocol-only consumer needs:
  - per-node `Label` members (e.g. `SomeNode.Label.MEMBER`),
  - `NodeKind` members,
  usable at runtime for equality comparisons, while preserving the protocol module's existing type-annotation surface.
- Cross-backend behavioral equivalence: equality comparisons written against protocol-module enums behave identically whether the runtime CST originated from the Python backend or the Rust backend, under the existing canonical-name equality contract.
- **(Load-bearing.)** A **general, traversal-agnostic narrowing primitive**: native `.kind` discrimination. A protocol-only consumer narrows a single child-union element to its concrete protocol node type **on demand** by comparing/matching `child.kind` against `cst.<Node>.kind`, cast-free and suppression-free, and **composes that into any traversal pattern they write themselves** (match/case dispatch, index walk, sibling walk, interleaved item/separator pairing, recursion — the consumer's choice). The discriminant is **per node TYPE**, **never per traversal pattern**. Settled mechanism (`narrowing-mechanism-probe.md`, "BOTTOM LINE" + Question A/D): native `match child.kind` / `if child.kind == cst.<Node>.kind` narrowing, enabled by every protocol node class exposing `kind` as a runtime Literal-typed class attribute and the shared `terminalsrc.Span` carrying `kind: Literal[SpanKind.SPAN]`. **No generated `TypeIs`/`TypeGuard` predicates and no traversal accessors are emitted** — native discrimination already delivers cross-enum, cross-backend narrowing (probe A2, D1-D4). This is distinct from the enum-value work below: exploration (§3 line 208, §5 line 204) establishes enum runtime values alone do not narrow a child-union element. See **Rejected approaches**.
- `fltk2gsm.py` converted to a clean protocol-only consumer per the gating criterion. `fltk2gsm.py` is the **model** consumer that must **consume** the general narrowing primitive exactly as an out-of-tree consumer would — it is **not** the spec, and its interleaved Items walk is **one call site**, not the shape the primitive is cut to.
- Backward-compatibility / breaking-change posture for the generated protocol module, which is public API for out-of-tree consumers.

## Out of scope

- Internal design: which module emits the enums, how values are assigned, generator structure, the mechanism of the narrowing primitive (`TypeIs`-style predicate, runtime-checkable protocol, node-only discriminated union, etc. — designer's choice, provided the output is general per **Rejected approaches**).
- Test plan / test code (acceptance criteria below state observable conditions only).
- Suppressions a consumer needs for reasons unrelated to the CST surface — *except* `S101`, which is now in scope per authoritative user direction (see Constraints: `S101` dropped from ruff selection). Shape 1's narrowing `assert` must be **bare** (no `# noqa: S101`), so `S101` is removed from the ruff selection rather than suppressed per-line.
- Changing the equality contract itself (canonical-name bridge semantics are fixed; this work conforms to them, does not alter them).
- `@typing.runtime_checkable` on Protocol classes (not required, not added).
- Making `fltk2gsm.py` *execute* against Rust-backend-produced CST. It consumes the Python concrete backend today (exploration line 107); no Rust execution baseline exists for it. This work does not add Rust-execution capability or output-parity-under-Rust to `fltk2gsm.py`. The cross-backend guarantee here is the *equality/hash* contract (AC 7), evaluated on enum members, not end-to-end execution of this consumer on Rust CST.

## Rejected approaches

- **Bespoke per-traversal accessor (REJECTED — twice, by the user).** A generated method whose shape is cut to one consumer's traversal pattern — e.g. `children_items_with_separators()` (interleaved item+separator pairing) or any method that bakes a specific walk into the generated surface — is **rejected and banned**. Do not re-propose it under a new name. If a design re-introduces a per-traversal accessor, it has **failed** this requirement.
  - **Rationale.** FLTK's generated surface is public API for **out-of-tree consumers** (CLAUDE.md, top level). A traversal-shaped accessor solves only the in-tree `fltk2gsm.py` Items walk — the *model* consumer's specific use case — and leaves every out-of-tree consumer who writes a *different* traversal (match dispatch, sibling walk, recursion, index walk) without a clean path. It is a point solution masquerading as generality. `fltk2gsm.py` is a model user, **not** the target user and **not** the spec.
  - **Why this keeps recurring (do not regenerate it).** `fltk2gsm.py` is the only consumer visible in-repo, so authors optimize against visible evidence and cut the accessor to its shape; "make fltk2gsm clean" is concrete and testable while "general primitive" is abstract; and generality was previously mis-operationalized as "another grammar of the same item/separator shape," which a point solution trivially passes. AC 11 closes this hole by requiring **structurally different traversal patterns**, which a traversal-shaped accessor cannot satisfy.
  - **Required output instead.** The general, traversal-agnostic narrowing primitive (see In scope / System behavior): native `.kind` discrimination keyed per node TYPE, composed by the consumer into their own walk. **Settled** (not "leading candidate"): native `match child.kind` / `if child.kind == cst.<Node>.kind` narrowing via Literal-typed `kind` class attributes; the `match`/`if` arm reference is `cst.<Node>.kind`, never an enum-namespace name. No generated `TypeIs`/`TypeGuard` predicates are emitted (probe shows native discrimination suffices; `narrowing-mechanism-probe.md` BOTTOM LINE).
- **`@typing.runtime_checkable` + `isinstance` (REJECTED).** Data-member protocols are not usefully runtime-checkable; rejected in a prior cycle. Not the narrowing mechanism. Not added.
- **`TypeIs`/`TypeGuard` predicates as the PRIMARY narrowing surface (REJECTED for this work).** Native `.kind` discrimination already delivers cross-enum, cross-backend narrowing in every consumer-authored traversal (probe A2/D1-D4/E*), so no generated narrowing predicates are emitted. (See `notes-design-user.md` for the prior-session provenance of the `TypeIs` line of thought; superseded here by the native-`.kind` probe result.)

## System behavior

### Protocol-module enum values at runtime

- Importing only the generated protocol module gives a consumer runtime-usable enum values:
  - `<ProtocolNode>.Label.<MEMBER>` resolves to a runtime object (not an unbound annotation) for every label declared on that node.
  - `NodeKind.<MEMBER>` resolves to a runtime object for every grammar rule.
- These runtime values are usable in `==` / `!=` comparisons.
- The protocol module's **type surface is preserved**: a protocol-only consumer's annotations against protocol types continue to type-check, and the change does not force out-of-tree consumers to edit their type annotations or call sites wholesale.

### Cross-backend equality

- For any label member `L` obtained from the protocol module and any concrete CST value `v` (whose label/kind attribute corresponds to `L`):
  - `protocol_label == v_label` is `True` when the canonical names match, `False` otherwise,
  - identically for a runtime CST produced by the **Python** backend and by the **Rust** backend.
- Same for `NodeKind` members obtained from the protocol module compared against `.kind` of either backend's nodes.
- Equality is defined via the existing canonical-name bridge; the comparison is symmetric (works regardless of operand order) under that contract.
- Hashing is consistent with equality: protocol-module enum members that compare equal to a backend member hash equal to it.

#### Three distinct enum classes (the load-bearing invariant)

At runtime `child` is a **concrete backend instance** — Python `fltk_cst` OR Rust — whose `.kind` is **that backend's own enum member**, a class DIFFERENT from the protocol module's `cst.<Node>.kind`. Native `.kind` discrimination (Shapes 1 and 2) therefore compares across up to **three distinct enum classes**: protocol-module, Python-concrete, Rust-concrete.

- `==` AND `!=` must behave correctly across all three: **equal iff identical canonical string** (`"NodeKind.<UPPER>"`), unequal otherwise.
- Per probe E3: in a `match`/`if`, the concrete instance is the comparison subject, so the concrete backend's own `__eq__` resolves the comparison against the protocol module's distinct `kind` object. **Agreement of the canonical string across protocol / Python-concrete / Rust-concrete is the single load-bearing invariant** — all three emit it identically.
- Both Shape 1 and Shape 2 must work identically regardless of which backend produced the node tree, with NO backend-specific code path and NO enum-namespace exposure.

> **Public API contract (settled):** The supported cross-enum comparison contract is `==` / `!=` only. Object identity (`is`) is **not** part of the contract and is **not** guaranteed — distinct modules/backends may produce distinct objects, so `node.kind is NodeKind.ITEM` may be `False` even when `node.kind == NodeKind.ITEM` is `True`. `match`/`case` value patterns (which dispatch via `==`) keep working across the protocol and concrete enum sets. This is the documented public-API contract for out-of-tree consumers.

### General narrowing primitive (traversal-agnostic) — native `.kind`

- Mechanism (settled, `narrowing-mechanism-probe.md`): each protocol node class exposes `kind` as a **runtime, Literal-typed class attribute** (`<Node>.kind: Literal[NodeKind.<X>]`); the shared `terminalsrc.Span` gains `SpanKind.SPAN` and `kind: Literal[SpanKind.SPAN]`. A protocol-only consumer narrows a **single** child-union element by comparing/matching `child.kind` against `cst.<Node>.kind` — statically and runtime-correct, no `typing.cast`, no CST-forced suppression.
- The discriminant is **per node TYPE**, **never per traversal pattern**. It narrows one element; it does not encode a walk.
- The consumer **composes** native `.kind` discrimination into whatever traversal they write: `match`/`case` dispatch (`case cst.<Node>.kind:`), `if`/`elif` (`child.kind == cst.<Node>.kind`), index walk, sibling walk, interleaved (child, separator) pairing, recursion — their choice. The mechanism privileges none.
- The `match child.kind` / `if child.kind == cst.<Node>.kind` arm references the discriminant ONLY as `cst.<Node>.kind`; the `NodeKind` / `SpanKind` enum names are **not** exposed in consumer code (probe D3/D4).
- The ordered, interleaved (child, separator-label) walk in `fltk2gsm.py` (Shape 1) is **one example** composition — **not** the definition of the capability. Heterogeneous match dispatch (Shape 2) is another.
- Delivered by native `.kind` discrimination, **not** by enum runtime values: per exploration §3/§5, enum values alone do not narrow a child-union element.
- `Span`-safety: `Span` carries its own `SpanKind.SPAN` Literal in a separate enum; pyright narrows the union even though `Span.kind`'s literal comes from a different enum than `NodeKind` (probe A2). No coupling between the shared `Span` and any per-grammar `NodeKind` is required.
- Eliminating a cast by substituting any other CST-forced suppression (`# type: ignore`, `# pyright: ignore`, `# noqa`) does **not** satisfy this requirement or the gating criterion.

### `fltk2gsm.py` end-to-end

After this work, `fltk2gsm.py`:

- imports **only** the generated protocol module for CST types and values (no `from ... import fltk_cst` runtime import; no `TYPE_CHECKING`-guarded `fltk_cst_protocol as cst` shadow; no dual binding of the same logical name);
- contains **no** `typing.cast` forced by CST types, including the two casts at the interleaved item/separator walk (`fltk2gsm.py:63`, `75`);
- contains **no** `# noqa` / pyright-ignore / ruff suppression *forced by the CST surface*;
- behaves identically to before (same GSM produced from the same input), under both backends.

## User-visible surface

- **Generated protocol module:** gains runtime enum values for per-node `Label` members and `NodeKind` members. Member names and canonical-name strings are unchanged from the concrete backends' (`"NodeKind.<UPPER>"`, `"<ClassName>.Label.<UPPER>"`).
- **Protocol node `kind` attribute:** each protocol node class exposes `kind` as a **runtime, Literal-typed class attribute** (`<Node>.kind: Literal[NodeKind.<X>]`), readable on the class object as `cst.<Node>.kind` and yielding the narrow Literal value (probe D4). This is the consumer narrowing surface.
- **`NodeKind` (and `SpanKind`):** `NodeKind` is **retained as public API** and as the Literal carrier in `kind` annotations, but is **not** the consumer narrowing surface — consumers reference `cst.<Node>.kind`, never the enum name. The enum namespace stays an implementation detail (probe D3).
- **Shared `terminalsrc.Span`:** gains a library-level `SpanKind` enum with member `SPAN` and a field `kind: Literal[SpanKind.SPAN] = SpanKind.SPAN`, placed after existing defaulted fields, compatible with `frozen=True, slots=True` (probe A4). This makes `Span` participate in native `.kind` narrowing without coupling to any per-grammar `NodeKind`.
- **Type surface:** unchanged in a backward-compatible direction — existing protocol annotations remain valid; consumers are not forced into annotation churn.
- No new required imports are imposed on consumers to obtain values (values come from the protocol module they already import).
- No renames of generated public symbols.

## Constraints

- **Public-API / breaking change (out-of-tree consumers):** the protocol module is public API. Changing per-node `Label` members from annotation-only (`ClassVar[object]`, no runtime value) to carrying runtime values is a structural change to that public API.
  - Acceptance posture: the change must be **additive and non-breaking** for existing out-of-tree consumers — code that reads `SomeNode.Label.MEMBER` or uses protocol annotations must continue to work and type-check. If any consumer-observable break is unavoidable, it must be a deliberate, called-out decision (see Open questions: `protocol-label-type-change`), not an incidental side effect.
  - No `Node`-suffix-style renames or annotation-forcing changes (per top-level CLAUDE.md).
- **Cross-backend equivalence** is evaluated from the out-of-tree consumer's perspective: comparisons written once against protocol-module enums work against both Python and Rust runtimes without consumer code changes.
- **`S101` dropped from ruff selection (authoritative user direction).** `S101` (assert-in-non-test) is removed from the project's ruff rule selection so the Shape-1 narrowing `assert item.kind == cst.Item.kind` is **bare** — no `# noqa: S101`. The narrowing assert is a first-class part of the supported consumer pattern; per-line suppression of it is unacceptable.
- **Shared `Span` carries `SpanKind`.** `terminalsrc.Span` gains `SpanKind.SPAN` + `kind: Literal[SpanKind.SPAN]` (field after existing defaulted fields; `frozen`/`slots`-compatible). `SpanKind` is a separate library-level enum with no dependency on any per-grammar `NodeKind` (probe A2/A4).
- **No generated `TypeIs`/`TypeGuard` predicates and no traversal accessors** are emitted; native `.kind` discrimination is the sole narrowing mechanism.
- **No new file-level suppressions** introduced into the generated protocol module as a side effect. The pre-existing `# ruff: noqa: N802` is not consumer-induced and is out of scope to remove.
- **No runtime-cost regression** imposed on consumers who do not use the new values: merely importing the protocol module must not eagerly import a *concrete backend* (Python or Rust), nor introduce any non-trivial runtime cost. The protocol module's own lightweight enum value objects (the necessary runtime footprint of this feature) are explicitly permitted — the bar is "no eager concrete-backend import / no heavy dependency," not "zero new runtime objects." **Settled (Option A):** the protocol module owns its own runtime `NodeKind` values and must **not** eagerly import a concrete backend (Python or Rust) at module load. (`fltk2gsm.py` does not reference `NodeKind`; this constraint protects general out-of-tree consumers.)

## Acceptance criteria (verifiable)

1. `fltk2gsm.py` imports exactly one CST module — the generated protocol module — and no concrete CST module, at runtime or under `TYPE_CHECKING`.
2. `fltk2gsm.py` contains zero `typing.cast` calls forced by CST types (specifically none at the former `:63`/`:75` interleaved walk).
3. `fltk2gsm.py` contains zero `# noqa` / pyright / ruff suppressions, including the narrowing asserts: `S101` is dropped from ruff selection, so Shape-1 asserts are **bare**.
4. `pyright` is clean on `fltk2gsm.py` with zero CST-forced suppressions in place.
5. `ruff check` is clean on `fltk2gsm.py` with zero CST-forced suppressions in place.
6. Importing only the protocol module, `<ProtocolNode>.Label.<MEMBER>` and `NodeKind.<MEMBER>` are runtime objects usable in `==`/`!=`.
7. A protocol-module `Label` member compares `==` to the corresponding label on a runtime CST node produced by the **Python** backend, and equally to one produced by the **Rust** backend; non-corresponding members compare `!=`. Same for `NodeKind` vs `.kind`. Hashing is consistent with this equality.
8. A protocol-only consumer can take a single arbitrary child-union element and narrow it to its concrete protocol node type via native `.kind` discrimination (`match child.kind: case cst.<Node>.kind` or `if child.kind == cst.<Node>.kind`), referencing the discriminant only as `cst.<Node>.kind`, with no CST-forced cast and no CST-forced suppression — independent of any surrounding traversal. `fltk2gsm.py`'s interleaved walk is satisfied by composing this at one call site (Shape 1).
   - 8a. **Shapes reproduced.** Both **Required consumer-code shapes** (Shape 1, Shape 2) type-check under pyright and pass `ruff check` importing ONLY the protocol module, with no `cast`, no `TYPE_CHECKING` shadow, no `@runtime_checkable`, no CST-forced suppression, and no bare `# noqa: S101`. A design/implementation that cannot reproduce both shapes (modulo names) FAILS.
9. `fltk2gsm.py` produces the same GSM output as before for the same inputs, against the backend it actually consumes (the Python concrete backend; see Out of scope re: Rust execution). Cross-backend guarantees are confined to AC 7 (equality/hash), which is the request's actual cross-backend concern.
10. Existing out-of-tree-style usage of the protocol module (reading `SomeNode.Label.MEMBER`; annotating with protocol types) remains valid and type-checks — the protocol-module change is additive/non-breaking (or, if not, the break is explicitly accepted under `protocol-label-type-change`).
11. **Generality (traversal-agnostic).** The narrowing primitive is exercised, importing only the protocol module, across **at least two STRUCTURALLY DIFFERENT traversal patterns** — e.g. a `match`/`case` dispatch over a child by node type AND an interleaved (child, separator) walk — each cast-free and CST-suppression-free. Two grammars of the *same* item/separator shape do **not** satisfy this; the criterion is multiple *traversal shapes*, not multiple grammars. A traversal-shaped accessor cut to a single walk (see **Rejected approaches**) is, by construction, **UNABLE** to satisfy this criterion. Together with AC 1-5/8, this establishes that *any* protocol-only consumer obtains (a) runtime enum values for `==`/`!=` and (b) the general per-element narrowing primitive composable into their own traversals. `fltk2gsm.py` is the model instance and one call site, not the spec.
12. **Cross-backend dual-shape dispatch.** A protocol-only consumer running BOTH Shape 1 and Shape 2 against BOTH a **Python-produced** and a **Rust-produced** node tree yields **identical, correct** dispatch/narrowing. At runtime `child.kind` is the concrete backend's own enum member (a class distinct from the protocol module's `cst.<Node>.kind`); `==`/`!=` resolve correctly across the three distinct enum classes (protocol, Python-concrete, Rust-concrete) via canonical-string agreement (`"NodeKind.<UPPER>"`) — equal iff identical canonical string, unequal otherwise. No backend-specific code path; no enum-namespace exposure (probe E1-E4).

## Open questions

- **`protocol-label-type-change`** — *(Not a user fork — designer-to-validate. Escalate to the user ONLY if Option A proves infeasible.)* The protocol `Label` is currently a plain class with `ClassVar[object]` members, deliberately structurally *distinct* from the concrete `enum.Enum` Label, and a test (`test_boundary_probe_documents_label_mismatch`, `test_cst_protocol.py:359-376`) asserts concrete is **not** assignable to the protocol type. Giving the protocol Label runtime values must not change its annotated type/structure.
  - **Required path: Option A** — add runtime values while keeping the members' annotated type, so existing protocol annotations and the structural-mismatch contract are preserved (purely additive — members go from no-value to having-a-value without changing their static type). Option B (changing the protocol `Label` to an enum, revising the structural-mismatch test, accepting a consumer-visible type change) is a breaking change forbidden by CLAUDE.md without explicit called-out justification and is **not** a designer default.
  - **Designer must validate, in design, that A is feasible:** (1) a value-carrying member typed `object` round-trips through the canonical-name bridge (`_fltk_canonical_name` is duck-typed — any object carrying the right canonical-name string compares equal), and (2) `test_boundary_probe_documents_label_mismatch` still passes (the protocol Label stays a non-enum plain class, so the structural mismatch with concrete `enum.Enum` is preserved). Both appear resolvable by code inspection (triage doc, §A).
  - **Escalation rule:** A is the mandated target. The designer does **not** silently flip A→B. If A proves infeasible — the structural-mismatch test cannot be kept passing, or the member cannot be typed cleanly without a CST-forced suppression in the generated module (forbidden by Constraints) — the designer escalates to the user with specific evidence and obtains explicit sign-off before adopting B.
