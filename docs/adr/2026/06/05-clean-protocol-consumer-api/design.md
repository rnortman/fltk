# Design: Clean Protocol-Only Consumer API

> Authoring note (applies to this doc): Concise. Precise. Complete. Unambiguous. No padding. No
> line-by-line diffs. Audience: smart LLM/human reviewer. This doc refers to `requirements.md`,
> `exploration.md`, `narrowing-mechanism-probe.md`, and `notes-design-user.md` rather than restating
> them. Citations are `file:line` against the working tree.

Requirements (LOCKED): `./requirements.md`. The "Required consumer-code shapes" (Shape 1 + Shape 2)
and AC 12 are the normative anchor. Exploration: `./exploration.md`. Empirical mechanism evidence:
`./narrowing-mechanism-probe.md` (probe IDs cited inline; not re-derived). User directive (rejected
approaches): `./notes-design-user.md`.

Outputs of this work: changes to the two generators (`fltk/fegen/gsm2tree.py`,
`fltk/fegen/gsm2tree_rs.py`), the shared runtime `fltk/fegen/pyrt/terminalsrc.py`, the Rust `Span`
pyclass (`src/span.rs`), the project ruff selection (`pyproject.toml`), the regenerated public-API
artifacts (`fltk_cst_protocol.py`, `fltk_cst.py`, Rust `_native`), and the rewritten consumer
`fltk/fegen/fltk2gsm.py`. No change to the canonical-name equality contract.

---

## 0. Decision / plan of record (do not re-litigate)

**Committed mechanism: native `.kind` discrimination.** Every protocol node class exposes `kind` as a
**runtime, `Literal`-typed class attribute** (`<Node>.kind: Literal[NodeKind.<X>]` with a runtime
default value). The shared `terminalsrc.Span` and the Rust `fltk._native.Span` each gain a
`SpanKind.SPAN`-valued `kind`. A protocol-only consumer narrows a single child-union element on demand
by comparing/matching `child.kind` against `cst.<Node>.kind` (`match child.kind: case cst.<Node>.kind`
or `if child.kind == cst.<Node>.kind`), referencing the discriminant ONLY as `cst.<Node>.kind`. This
is statically correct (probe A2, D1–D4) and cross-backend runtime-correct via the canonical-name
bridge (probe E1–E4). The consumer composes it into any traversal they write; the discriminant is per
node TYPE, never per traversal pattern.

**Rejected, do not re-propose (per `notes-design-user.md`, rejected TWICE by the user):**

- **Bespoke per-traversal accessor** (e.g. `children_items_with_separators()`) — banned. It serves only
  the in-tree `fltk2gsm.py` Items walk and leaves every out-of-tree consumer who writes a different
  traversal without a clean path. AC 11 (two *structurally different* traversal shapes) is constructed
  so a traversal-shaped accessor cannot pass.
- **`@typing.runtime_checkable` + `isinstance`** — data-member protocols are not usefully
  runtime-checkable; rejected in a prior cycle. Not added.
- **`TypeIs`/`TypeGuard` predicates as the PRIMARY narrowing surface** — native `.kind` discrimination
  already delivers cross-enum, cross-backend narrowing in every consumer-authored traversal (probe
  A2/D1–D4/E*), so **no generated narrowing predicates are emitted**. (`notes-design-user.md` records
  the prior-session `TypeIs` line of thought; superseded here by the native-`.kind` probe result. The
  earlier `TypeIs` plan-of-record from `notes-design-user.md §"COMMITTED MECHANISM"` is explicitly
  overridden by the locked requirements + probe, which name native `.kind` as the settled mechanism —
  see `requirements.md` "Rejected approaches" / `narrowing-mechanism-probe.md` BOTTOM LINE.)

---

## 1. Root cause / context

The protocol module `fltk_cst_protocol.py` is public API for out-of-tree consumers (CLAUDE.md). Today
it cannot serve as a *clean*, single-import CST surface, forcing the gating-criterion violations
documented in `exploration.md §3`:

1. **No runtime enum values.** Protocol `Label` members are bare `ClassVar[object]` annotations with no
   runtime value (`gsm2tree.py:476-483`; emitted at `fltk_cst_protocol.py:14`, `39`, ...). `NodeKind`
   is imported only under `TYPE_CHECKING` (`gsm2tree.py:451-454`), lazy-string via `from __future__
   import annotations` (`gsm2tree.py:438`). So a consumer who needs values at runtime
   (`cst.Items.Label.NO_WS`, `cst.Item.kind`) must *also* import the concrete module — forcing the dual
   import / `TYPE_CHECKING` shadow in `fltk2gsm.py:8,11-12`.

2. **No per-element narrowing.** `kind` is annotation-only (`gsm2tree.py:488-489`), so `cst.<Node>.kind`
   is not a runtime value and `child.kind == cst.<Node>.kind` cannot narrow at runtime; `fltk2gsm.py`
   resorts to `typing.cast` at `:63` and `:75`. Per `exploration.md §3/§5`, enum runtime values **alone**
   do not narrow a child-union element — the narrowing comes specifically from `kind` being a
   `Literal`-typed value readable on the class.

3. **`Span` is not `kind`-discriminable.** Separator children land in the `Item | Trivia |
   terminalsrc.Span` union (`fltk_cst.py:298`). `terminalsrc.Span` has no `kind` (`terminalsrc.py:7-91`),
   so `case cst.Span.kind:` cannot exist as a value pattern and the `Span` arm of the union cannot be
   narrowed natively.

4. **Three distinct runtime `Span` types.** Confirmed: the static child-union type is the Python
   `terminalsrc.Span` (`fltk_cst.py:298`), but at runtime separators are backend-specific concrete
   objects:
   - Python concrete backend attaches `terminalsrc.Span` (`fltk_parser.py:338,342,345`,
     `append_no_ws(child=<Span>)`).
   - Rust backend attaches its own `#[pyclass] Span` = `fltk._native.Span` (`src/span.rs:56-62`;
     node `span`/separator children are `PyObject` initialised to `fltk._native.UnknownSpan`,
     `cst_fegen.rs:153-163`). This is a **different class** from `terminalsrc.Span`.

   So Shape 2's `case cst.Span.kind:` must narrow *statically* against `terminalsrc.Span.kind` (pyright)
   AND dispatch *at runtime* correctly when the concrete object is either a Python `terminalsrc.Span`
   or a Rust `fltk._native.Span`. This is the AC 12 "distinct enum classes" problem on the
   `Span`/`SpanKind` axis. Note: the Python concrete backend has no `Span` class of its own — it uses the
   shared `terminalsrc.Span` (`fltk_cst.py:5,75,298`), so the protocol reference (`cst.Span.kind`) and
   the Python-concrete runtime object resolve to the *same* `SpanKind.SPAN`. §2.2 makes the Rust getter
   return that same object too, collapsing this axis to a single `SpanKind.SPAN` value at runtime (in
   contrast to the `NodeKind` axis, which genuinely has three distinct classes — protocol-local, Python
   concrete, Rust).

The cross-backend equality contract is already in place and unchanged: `NodeKind`/`Label` carry
`_fltk_canonical_name` and a duck-typed bridge `__eq__`/`__hash__` (`gsm2tree.py:100-132`,
`fltk_cst.py:25-36`; Rust `gsm2tree_rs.py:150-179`). A third enum set compares equal to both backends
iff it emits the identical canonical string and exposes `_fltk_canonical_name` (`exploration.md
§2/§4`). This design extends that exact pattern to `SpanKind` and to the protocol module's own
runtime enums.

---

## 2. Proposed approach

Five production changes (§2.1–§2.5) plus a test-only reference consumer (§2.6). All generated symbols
are **additive**; nothing is renamed (CLAUDE.md breaking-change rules — see §5).

### 2.1 Shared `terminalsrc.Span` gains `SpanKind` + `kind` (Python runtime)

In `fltk/fegen/pyrt/terminalsrc.py` (hand-written shared library, not generated):

- Add a module-level enum carrying the cross-backend bridge:
  ```python
  class SpanKind(enum.Enum):
      SPAN = enum.auto()
  ```
  with the same `__eq__`/`__hash__`/`_fltk_canonical_name` bridge shape the generators emit for
  `NodeKind` (`gsm2tree.py:100-132`), and `SpanKind.SPAN._fltk_canonical_name = "SpanKind.SPAN"`
  assigned post-class. This is the single `SpanKind.SPAN` value for the whole `Span` axis: the protocol
  reference, the Python-concrete `Span.kind`, and the Rust `Span.kind` getter (§2.2) all resolve to it,
  so the bridge `__eq__` is defensive insurance (never actually invoked cross-class in the recommended
  realization, where every operand is the same object). Hand-write the bridge anyway to mirror the
  generated pattern and stay robust if a future Rust realization introduces a separate `SpanKind`.
- Add one field to `Span`, **after** the existing defaulted `_source` (default-after-default ordering
  is mandatory on a dataclass; probe A4 confirms `frozen=True, slots=True` compatibility and that the
  constant default never breaks `==`):
  ```python
  kind: Literal[SpanKind.SPAN] = field(default=SpanKind.SPAN, compare=False, hash=False)
  ```
  `compare=False, hash=False` is **REQUIRED**, not defensive polish. `terminalsrc.Span` is a
  `@dataclass(frozen, eq, slots)` whose `__eq__` is generated from compared fields; `_source` is already
  `compare=False, hash=False` (`terminalsrc.py:13`) to preserve the documented "sourceless sentinel `==`
  source-bearing span at same position" invariant (mirrored in `src/span.rs:51-53`). Adding a third
  compared field — even a constant — is exactly the change that invariant guards, so excluding `kind` from
  compare/hash is mandatory to keep the contract robust against future edits. (Because `kind` is constant
  the `==` result is unchanged either way, so equality is correct regardless; the requirement is to keep
  it OUT of the compared set permanently.) `kind` lands in `__slots__`
  (probe A4). Readable as `terminalsrc.Span.kind` on the class → `Literal[SpanKind.SPAN]` (probe D4),
  which is what makes the `case cst.Span.kind:` value pattern narrow.

`SpanKind` has **no dependency** on any per-grammar `NodeKind` (probe A2 proves cross-enum literals
still narrow the union). No coupling required.

### 2.2 Rust `Span` gains a `kind` getter bridged to `SpanKind` (Rust runtime)

In `src/span.rs` (the `#[pyclass] Span`), add a `#[getter] fn kind` returning a Python object that is
`==`-equal to `SpanKind.SPAN` across backends. Because the *static* union type is `terminalsrc.Span`
and the consumer references the discriminant only as `cst.Span.kind` (which resolves to the Python
`SpanKind.SPAN`), the Rust side only needs **runtime** equality, via the canonical-name bridge:

- The Rust `Span.kind` getter returns an object whose `_fltk_canonical_name == "SpanKind.SPAN"` and
  whose `__eq__` is the cross-backend bridge (`other.getattr("_fltk_canonical_name")` then compare),
  mirroring `_emit_rust_cross_backend_eq_hash` (`gsm2tree_rs.py:150-179`).
- Simplest realization: import and return the shared Python `SpanKind.SPAN` directly
  (`py.import("fltk.fegen.pyrt.terminalsrc")?.getattr("SpanKind")?.getattr("SPAN")`), cached in a
  `GILOnceCell` using the **same `GILOnceCell` pattern** as `UNKNOWN_SPAN_CACHE` (`cst_fegen.rs`
  preamble, `lib.rs:10-33`) but in the **opposite import direction**. `UNKNOWN_SPAN_CACHE` is
  generated-Python → `fltk._native`; this getter is `fltk._native` → pure-Python
  `fltk.fegen.pyrt.terminalsrc`. **Acyclicity invariant (load-bearing, must hold): `terminalsrc` must
  never import `fltk._native`.** Verified at design time: `terminalsrc.py` imports only `bisect`, `re`,
  `dataclasses`, `typing` (`terminalsrc.py:1-4`) — no native import, so no cycle today. If a future change
  makes `terminalsrc` import the native extension, this cached cross-direction import becomes an import
  cycle (deadlock / init failure) at first `Span.kind` access; the Rust-`#[pyclass] SpanKind` fallback
  below is the escape hatch. Returning the *same* Python enum object means equality is trivially
  satisfied and there is no second `SpanKind` class to keep in canonical-string sync. **This is the
  recommended realization** — it makes the
  "three distinct enum classes" collapse to two on the `Span` axis (protocol/Python share one
  `SpanKind`; Rust returns that same object), which strictly simplifies the invariant.
  - OPEN DETAIL — RESOLVED: the Rust backend yields a **distinct** `Span` class (`fltk._native.Span`),
    NOT the shared `terminalsrc.Span` (`src/span.rs:56`, `lib.rs:22`). Its `kind` discriminant is
    bridged by having the getter *return the shared Python `SpanKind.SPAN`*, so no separate Rust
    `SpanKind` enum is introduced. If a future change makes Rust `Span` opaque again or forbids the
    cross-crate import, fall back to a Rust `#[pyclass] SpanKind` carrying the identical
    `"SpanKind.SPAN"` canonical string + bridge (the `NodeKind` Rust pattern), at the cost of a third
    enum class to keep in sync.

### 2.3 Protocol module: runtime `kind` values + runtime `Label`/`NodeKind` values (Part A)

In `gsm2tree.py:gen_protocol_module` / `_protocol_class_for_model`:

**(a) `NodeKind` owned by the protocol module at runtime (Constraint "Option A", settled).** Replace the
`TYPE_CHECKING`-only `from <concrete> import NodeKind` (`gsm2tree.py:451-454`) with a **protocol-module-
local** runtime `NodeKind` enum, emitted by reusing the existing `_node_kind_enum()` +
`_emit_node_kind_canonical_name_assignments()` (`gsm2tree.py:134-156`) so it carries the identical
member names, canonical strings (`"NodeKind.<UPPER>"`), and the cross-backend bridge. The protocol
module must **not** eagerly import any concrete backend at module load (Constraint: no runtime-cost
regression; `fltk2gsm.py` does not reference `NodeKind`, but general consumers may). Emit `import enum`
in the protocol module. The `Literal[NodeKind.<X>]` annotations now reference this local `NodeKind`.

**(b) `kind` as a runtime `Literal`-typed class attribute.** Change the `kind` emission
(`gsm2tree.py:488-489`) from a bare annotation to an annotation **with a runtime default**:
```python
kind: typing.Literal[NodeKind.<X>] = NodeKind.<X>
```
On a `typing.Protocol` class this default is a class attribute readable as `cst.<Node>.kind`, typed
`Literal[NodeKind.<X>]` (probe D4), and `==`-comparable. This is the consumer narrowing surface.
- Protocol classes are `typing.Protocol` (`gsm2tree.py:470`), not dataclasses; a plain class-level
  assignment `kind = NodeKind.<X>` with the `Literal` annotation is the mechanism. The Protocol still
  type-checks: concrete nodes structurally provide `kind` (probe-equivalent; the concrete `kind` is a
  matching `Literal`).

**(c) `Label` members gain runtime values, type unchanged (Option A — designer-validated below).** Change
each protocol `Label` member from `MEMBER: typing.ClassVar[object]` (`gsm2tree.py:483`) to a
value-carrying assignment whose *annotated type stays `object`*:
```python
MEMBER: typing.ClassVar[object] = <value>
```
where `<value>` is a tiny runtime sentinel carrying `_fltk_canonical_name = "<ClassName>.Label.<UPPER>"`
and the bridge `__eq__`/`__hash__`. Realization: a small module-level `_ProtocolLabelMember` class (or
reuse a generated bridge-bearing object) instantiated per label; assigned post-class like the existing
canonical-name assignments (`gsm2tree.py:158-169`), OR inline.

**The sentinel's `__eq__`/`__hash__` MUST be the EXACT `_emit_cross_backend_eq_hash` shape**
(`gsm2tree.py:117-132`), not an ad-hoc equality:
  - `__eq__`: identity fast-path (`if other is self: return True`); same-type fast-path; then
    `cn = getattr(other, '_fltk_canonical_name', None); if cn is not None: return
    self._fltk_canonical_name == cn`; then **`return NotImplemented` for foreign operands**.
  - `__hash__`: **`return hash(self._fltk_canonical_name)`**.
  This is load-bearing, not boilerplate. Shape 1 sites write the comparison with the *concrete* label as
  the LEFT operand (`item_label == cst.Items.Label.ITEM`, `fltk2gsm.py:45-51,62,65,67,70,74`), so the
  concrete enum's bridge `__eq__` (`gsm2tree.py:120-124`) resolves and the sentinel's `__eq__` is never
  reached there. But AC 7 requires **both operand orders** (symmetry) and AC 6 requires general `==`/`!=`
  usability — where the sentinel IS the subject/LEFT operand. A naive sentinel that (a) returns
  `True`/`False` for all foreign operands would give wrong results for non-matching operands and block the
  reflected `__eq__`; (b) uses an identity/`object`-default `__hash__` would make members that compare
  equal hash UNEQUAL, failing AC 7's hash clause and breaking set/dict membership. `NotImplemented` +
  canonical-name `__hash__` are mandatory.

The member's **static type remains `object`**, so:
  - the protocol `Label` stays a **plain class** (not `enum.Enum`), preserving the structural-mismatch
    contract (`test_cst_protocol.py:359-376`, `test_boundary_probe_documents_label_mismatch` — concrete
    `enum.Enum` Label is NOT assignable to the protocol plain-class Label). **Validated:** the test
    asserts a *structural* mismatch between `enum.Enum` and a plain class; adding a value typed `object`
    to a plain-class member does not make it an enum, so the mismatch is preserved.
  - existing out-of-tree code reading `SomeNode.Label.MEMBER` continues to type-check (`object` ←
    unchanged) and now also works at runtime in `==`/`!=` (`requirements.md` AC 6, AC 10).
  - **Bridge round-trip validated:** `_fltk_canonical_name` is duck-typed (`getattr(other,
    '_fltk_canonical_name', None)`, `gsm2tree.py:122`); any object exposing the right string compares
    equal to the concrete/Rust `Label` member. A value typed `object` round-trips (the bridge never
    inspects the static type).

This is purely additive (no-value → has-value, same static type), so AC 10 holds and the Open Question
`protocol-label-type-change` resolves to **Option A**, no user escalation needed.

### 2.4 `fltk2gsm.py` rewritten to Shape 1 (the model consumer)

Rewrite `fltk/fegen/fltk2gsm.py` to import **only** the protocol module and consume the general
primitive:

- Single import: `from fltk.fegen import fltk_cst_protocol as cst`. Delete the runtime
  `from fltk.fegen import fltk_cst as cst` (`:8`) and the `TYPE_CHECKING` shadow (`:11-12`). Delete
  `import typing` if it becomes unused, and the `TYPE_CHECKING` import.
- Replace both `typing.cast("cst.Item", item)` (`:63`, `:75`) with the bare narrowing assert:
  ```python
  assert item.kind == cst.Item.kind
  ```
  which narrows `item: Item | Trivia | Span → cst.Item` (probe D2: `if child.kind == Item.kind` narrows
  the outer `child`; probe A2: cross-enum literals narrow). No `cast`, no suppression.
- Remove all `# noqa: S101` (`:62,70,74,78`): the narrowing assert is **bare** (see §2.5). The
  label-equality asserts (`item_label == cst.Items.Label.ITEM`, etc.) remain but are likewise bare.
- The `cst.Items.Label.<MEMBER>` comparisons (`:45-51,62,65,67,70,74`) now resolve to runtime values
  from the protocol module (§2.3c). Behavior is identical (AC 9): same GSM from same input.
- The interleaved (item, separator) zip walk (`:59-77`) is preserved verbatim — it is ONE composition
  of the general primitive (Shape 1), not a generated accessor.

`fltk2gsm.py` continues to execute against the Python concrete backend only (`requirements.md` Out of
scope: no Rust-execution baseline added).

### 2.5 Drop `S101` from the ruff selection (project config)

In `pyproject.toml [tool.ruff.lint]`, the `S` rule family is selected (`pyproject.toml:83`). Per
authoritative user direction (`requirements.md` Constraints), remove `S101` (assert-in-non-test) so the
Shape-1 narrowing assert is bare project-wide. `S` is selected as a family, not individually; realize
the drop by adding `"S101"` to the `ignore` list (`pyproject.toml:90-99`) — this disables exactly S101
while keeping the rest of `S`. (The per-file-ignores for tests, `pyproject.toml:113-114`, already
exempt tests; this makes the assert bare in non-test modules like `fltk2gsm.py` too.) This is a
deliberate project-policy change, called out here.

### 2.6 Shape 2 reference consumer (test-only; not shipped in `fltk2gsm.py`)

Shape 2 (heterogeneous `match`/`case` dispatch) has no in-tree production call site. It is exercised by
a test consumer (see §4) importing only the protocol module:
```python
match child.kind:
    case cst.Item.kind:   ...   # child: cst.Item
    case cst.Trivia.kind: ...   # child: cst.Trivia
    case cst.Span.kind:   ...   # child: terminalsrc.Span
```
`case cst.<Node>.kind:` is a dotted-name VALUE pattern; pyright narrows the outer `child` per arm
(probe D1/D3). At runtime `match` evaluates `subject == pattern_value` (probe E3), so the concrete
backend instance is the subject and its bridge `__eq__` resolves against the protocol's distinct `kind`
object via canonical string — identical for Python and Rust subjects (probe E2/E4).

---

## 3. Edge cases / failure modes

- **Default-after-default ordering (`Span.kind`).** `Span` already has a defaulted `_source`
  (`terminalsrc.py:13`); `kind` MUST be declared after it or class creation raises `TypeError` (probe
  A4 caveat). Place `kind` last.
- **`Span` `==`/`hash` regression.** `Span` equality/hash currently use only `(start, end)`
  (`terminalsrc.py:7`, `_source` is `compare=False, hash=False`). Adding `kind` with
  `compare=False, hash=False` preserves this exactly. Failure mode if forgotten: spans at the same
  position stop comparing equal — guarded by an existing `Span`-equality test (see §4) plus the new
  field flags.
- **Three-enum canonical-string drift (the single load-bearing invariant).** Equality across protocol /
  Python-concrete / Rust-concrete rests entirely on identical canonical strings
  (`"NodeKind.<UPPER>"`, `"SpanKind.SPAN"`, `"<ClassName>.Label.<UPPER>"`). Drift in any emitter breaks
  `==`/`match` silently. Mitigation: the protocol `NodeKind` reuses the *same* generator helpers as the
  concrete `NodeKind` (`gsm2tree.py:95-156`), so they cannot drift; the Rust `Span.kind` returns the
  *shared* Python `SpanKind.SPAN` object (§2.2), eliminating a third `SpanKind` string entirely; the
  `SpanKind` bridge is hand-written once in `terminalsrc.py`. The AC-7/AC-12 cross-backend tests assert
  the invariant directly.
- **`is`-identity is NOT guaranteed (documented contract).** Distinct modules/backends produce distinct
  `kind`/`Label` objects, so `node.kind is NodeKind.ITEM` may be `False` even when `==` is `True`
  (`requirements.md` "Public API contract (settled)"). `match`/`case` dispatch via `==` and keeps
  working; consumers using `is` are out of contract. Any in-tree `is`-comparison of these enums would be
  a bug — `fltk2gsm.py` uses `==` throughout (`exploration.md §5`).
- **Protocol `Label` member typed `object` and `reportUndefinedVariable`.** The original `ClassVar[Label]`
  self-reference problem (`gsm2tree.py:478-482`) is why members are typed `object`; keeping `object`
  (not `Label`) avoids reintroducing that pyright error. Validated: the value assignment does not change
  the annotation.
- **Rust `UnknownSpan` separator children.** Rust separator/`span` slots default to
  `fltk._native.UnknownSpan` (`cst_fegen.rs:153-163`), which is a Rust `Span` and therefore exposes the
  new `kind` getter — so `case cst.Span.kind:` narrows it too. No `getattr`-miss path needed (native
  discrimination, not a `TypeIs` body).
- **Protocol module runtime cost.** Adding a local `NodeKind` enum + per-label sentinel objects adds
  lightweight runtime objects only; it must NOT eagerly import a concrete backend (Constraint). The
  `from <concrete> import NodeKind` import is *removed*, not promoted to runtime — the protocol owns its
  own `NodeKind`. Verify the regenerated module imports only `enum`, `typing`, `terminalsrc`.
- **`# ruff: noqa: N802`** on the protocol module (`fltk_cst_protocol.py:1`) is pre-existing and not
  consumer-induced; retained, out of scope (Constraint).

---

## 4. Test plan

After this work, the following tests exist (TDD: write failing first). Grammar under test is the
self-hosting `fegen` grammar (provides `Items` with the `Item | Trivia | Span` union and NO_WS /
WS_ALLOWED / WS_REQUIRED separators) plus the Rust fixture grammars under `tests/rust_cst_*`.

1. **Shape 1 + Shape 2 pyright+ruff clean (AC 8a, 11).** A test consumer module importing ONLY
   `fltk_cst_protocol` containing both shapes (interleaved item/separator walk AND `match`/`case`
   dispatch). Assert via subprocess `uv run pyright <module>` → 0 errors, and `uv run ruff check
   <module>` → clean, with NO `cast`, NO `TYPE_CHECKING` shadow, NO `@runtime_checkable`, NO
   CST-forced suppression, NO bare `# noqa: S101`. Two **structurally different** traversal shapes
   discharge AC 11 (a traversal accessor cannot satisfy this by construction).
2. **`fltk2gsm.py` cleanliness (AC 1–5).** Assert the module imports exactly one CST module
   (protocol), zero `typing.cast`, zero CST-forced suppressions; `uv run pyright fltk2gsm.py` and
   `uv run ruff check fltk2gsm.py` clean. (Can be a static-grep test + the existing lint gate.)
3. **`fltk2gsm.py` behavioral equivalence (AC 9).** Existing fegen self-host round-trip / GSM-output
   tests pass unchanged against the Python concrete backend.
4. **Runtime enum values (AC 6).** Importing only the protocol module, assert
   `cst.<Node>.Label.<MEMBER>` and `cst.NodeKind.<MEMBER>` are runtime objects usable in `==`/`!=`,
   and that importing the protocol module does NOT import a concrete backend. Assert specifically
   `"fltk.fegen.fltk_cst" not in sys.modules` AND `"fltk._native" not in sys.modules` after a fresh
   protocol import. **Do NOT** assert an over-strict "only `enum`+`typing`" allowlist: the protocol module
   already imports `fltk.fegen.pyrt.terminalsrc` (`fltk_cst_protocol.py:6`) and §2.1 adds `SpanKind` there
   — `terminalsrc` is the shared runtime (carries no `fltk._native`/`fltk_cst` import per §2.2 acyclicity
   invariant), so its presence is EXPECTED; an over-strict allowlist would false-fail on it.
5. **AC 7 cross-backend equality/hash.** For a `NodeKind` member and a `Label` member obtained from the
   protocol module: `==` a corresponding `.kind`/label on a node produced by the **Python** backend AND
   on a node produced by the **Rust** backend (`True`); non-corresponding members `!=` (`False`); equal
   members hash equal. **Both operand orders (symmetry)** — explicitly assert with the protocol-module
   member as the LEFT/subject operand, exercising the sentinel's own bridge `__eq__` (§2.3c), not only the
   concrete-LEFT order that Shape 1 uses. Include a matching AND a non-matching protocol `Label` member vs
   a concrete one in both orders, and assert `hash(proto_label) == hash(concrete_label)` for the matching
   pair. This directly guards the §2.3c sentinel `NotImplemented`/`__hash__` requirement.
6. **AC 12 cross-backend dual-shape dispatch (the load-bearing test).** A single protocol-only consumer
   runs BOTH Shape 1 and Shape 2 against BOTH a Python-produced and a Rust-produced tree of the same
   grammar; assert identical, correct dispatch/narrowing for all four (shape × backend) combinations,
   including the `case cst.Span.kind:` arm matching a Python `terminalsrc.Span` AND a Rust
   `fltk._native.Span` separator. No backend-specific code path; no enum-namespace name in the consumer.
7. **Canonical-string agreement invariant.** Assert
   `cst.NodeKind.<X>._fltk_canonical_name == <PythonConcrete>.NodeKind.<X>._fltk_canonical_name ==
   <RustNodeKind>.<X>._fltk_canonical_name` for every member, and likewise
   `"SpanKind.SPAN"` across `terminalsrc.SpanKind.SPAN`, a Python `Span().kind`, and a Rust
   `Span(...).kind` (which returns the shared object — so identity holds there). This directly guards
   the §3 drift failure mode.
8. **`Span` equality/hash unchanged.** Existing `Span`-equality tests pass; add an assertion that two
   `Span`s at the same `(start, end)` with differing/absent `kind`-irrelevant fields still compare
   equal and hash equal (guards the `compare=False, hash=False` requirement).
9. **Structural-mismatch contract preserved (Option A).** `test_boundary_probe_documents_label_mismatch`
   (`test_cst_protocol.py:359-376`) still passes: concrete `enum.Enum` Label remains non-assignable to
   the protocol plain-class Label.

---

## 5. Public-API / breaking-change posture

The protocol module is public API for out-of-tree consumers (CLAUDE.md). All changes are **additive**:

- **`NodeKind` retained** as public API and as the `Literal` carrier in `kind` annotations; member names
  and canonical strings unchanged. It moves from `TYPE_CHECKING`-only to protocol-owned runtime, which
  only *adds* runtime availability — existing annotation usage is unaffected.
- **`kind`** gains a runtime value; its static type (`Literal[NodeKind.<X>]`) is unchanged.
- **`Label` members** gain runtime values; static type stays `object` (Option A). No member renamed, no
  type narrowed/widened in a breaking direction. Existing `SomeNode.Label.MEMBER` reads keep working
  and type-checking (AC 10).
- **`terminalsrc.Span`** gains `SpanKind` + `kind` (additive field with a constant default; existing
  constructions `Span(start, end)` / `Span(start, end, source)` unchanged; `==`/`hash` unchanged).
- **No renames** of any generated public symbol; **no annotation churn** forced on consumers
  (CLAUDE.md). `NodeKind` is NOT the consumer narrowing surface — consumers reference `cst.<Node>.kind`
  only; the enum namespace stays an implementation detail (probe D3).

Consumer-visible contract additions: `cst.<Node>.kind` is a stable `==`-comparable `Literal` value;
cross-enum comparison is `==`/`!=` only (`is` not guaranteed); `match`/`case` value patterns work
across protocol/Python/Rust enum sets.

---

## 6. Open questions (genuine user-judgment only)

None blocking. The two formerly-open items are resolved in-design:

- **`protocol-label-type-change`** → resolved to **Option A** (value-carrying members typed `object`),
  validated in §2.3c and §3: bridge round-trips a value typed `object`, and the structural-mismatch
  test stays green. No user escalation (the requirement mandates A; escalate only if A proves
  infeasible, which it does not).
- **Rust `Span` discriminant bridging** → resolved (§2.2): Rust `Span.kind` returns the shared Python
  `SpanKind.SPAN` object; no separate Rust `SpanKind` class. (Recorded here so it is not re-opened: the
  Rust backend yields a *distinct* `Span` class but a *shared* `SpanKind` value.)
