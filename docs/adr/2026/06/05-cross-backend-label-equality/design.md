# Cross-Backend Label Equality + NodeKind Discriminant — Design

**Date:** 2026-06-05
**Mode:** draft
**Base commit:** a5cffc5 (working tree at HEAD 2258b08; only CLAUDE.md differs)
**Requirements:** `requirements.md` (this dir). **Exploration:** `exploration.md`. **Authoritative steer:** `notes-design-user.md`.
**Supporting:** `isinstance-vs-label-investigation.md`; `../05-cst-type-annotations-regression/trivia-divergence-rootcause-v2.md`, `node-suffix-investigation.md`.

> Style note (for any agent editing this doc): concise, precise, unambiguous. No padding, no requirements re-summary, no line-by-line diffs. State decisions and the reasons that constrain them.

This design realizes the settled mechanism decisions in `notes-design-user.md`. It does not re-litigate them; it works out generator wiring, edge cases, and tests, and surfaces any point where the working tree / pyright / PyO3 contradict the steer.

---

## 1. Root cause / context

Two independent but coupled problems, both rooted in generated code emitting backend-local type identity where a backend-independent key is needed.

### 1.1 Label equality is identity/type-scoped, not name-scoped

- **Python** (`gsm2tree.py:112-116`): each rule's `Label` is a bare `enum.Enum` with `enum.auto()` members. `enum.Enum.__eq__` is identity-based; members are singletons of one class. A Python `Items.Label.NO_WS` is never `==` a Rust `Items_Label::NoWs`. Ordinals come from sorted position, so even the int values are not a stable key (`exploration.md:22`).
- **Rust** (`gsm2tree_rs.py:151-160`): each `Label` is `#[pyclass(eq, hash, frozen)]` over `#[derive(PartialEq, Eq, Hash)]`. PyO3 derives `__eq__`/`__hash__` that compare **within the same Rust enum type only**; a foreign operand yields `NotImplemented` → `False`. Confirmed against `src/cst_fegen.rs:16` and the three separate crates (`src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`) — each compiles to a *distinct* Python type for the same grammar (`exploration.md:262`).
- **The stable key already exists** on the Rust side: `__repr__` returns the canonical string `"<ClassName>.Label.<LABEL_NAME>"` (`gsm2tree_rs.py:166-172`; baked at `src/cst_fegen.rs:27`). The Python side has no equivalent — its `repr` is `"<Label.NO_WS: 2>"`, `str` is `"Label.NO_WS"` (no class prefix; `exploration.md:43-44`).

Result: cross-backend comparisons silently return `False` (`exploration.md:240`). Out-of-tree consumers comparing a stored label against a module-level `cst.X.Label.Y` constant break the moment the stored label and the constant originate from different backends (`requirements.md:15`).

### 1.2 Type narrowing needs a node-borne discriminant, not label-keyed tuples

Consumers dispatch on node type. The natural idioms — `isinstance(node, self.cst.Item)` (`fltk2gsm.py:69,80`) and iterating `for label, child in node.children` then keying on `label` — both fail the cross-backend goal:

- `isinstance` against a PyO3 native class tests native type identity and **cannot** be satisfied by label equality (`exploration.md:190`). It is the hard blocker for removing `self.cst`.
- Label-keyed tuple-union discrimination fails pyright: destructuring `for label, child in node.children` severs the label↔child correlation, so pyright cannot narrow `child` from a test on `label` (no correlated unpacking). Settled in `notes-design-user.md:10`.

The settled answer (`notes-design-user.md:2`): a per-node attribute discriminant `kind: Literal[NodeKind.<Rule>]` that pyright narrows reliably and that works on a bare node with no parent. Its comparison (`node.kind == NodeKind.Item`) is itself a cross-backend enum `==`, so it rides on the §1.1 machinery — no separate equality mechanism.

### 1.3 Why the in-tree demonstration (`self.cst` removal) is load-bearing

`fltk2gsm.py` injects `self.cst` (`fltk2gsm.py:22`) so that stored labels and comparison constants always come from the *same* backend — which is exactly why cross-backend equality is not exercised today (`exploration.md:146,202`). Removing `self.cst` and comparing against a *single fixed* `cst` module's static constants forces the cross-backend path: a Rust-backend-parsed label is compared against a Python-module constant. The existing `test_*_rust_equals_python` parity tests then become the proof that equality holds for both backends (`requirements.md:100-102`).

---

## 2. Proposed approach

Two enum families gain a canonical-name-keyed equality/hash contract, co-emitted by both generators; a new `NodeKind` discriminant is added to every node; `fltk2gsm.py` drops `self.cst`. Everything is generator-emitted for every grammar (framework feature, `notes-design-user.md:17`).

### 2.1 Canonical name — the single equality key

Form: `"<ClassName>.Label.<LABEL_NAME>"` for labels (already the Rust `__repr__` string), and **`"NodeKind.<MEMBER>"`** for `NodeKind` members (family-prefixed). Rule+label scoped, no grammar identity (`requirements.md:48`; cross-grammar collision accepted per Open question §6.4 default).

**Family disjointness:** the two families share the *same* §2.1 marker-based eq path, so a `NodeKind` member and a `Label` member compare `==` iff their canonical strings coincide. The `Label` form (`"X.Label.Y"`, always containing `".Label."`) and the `NodeKind` form (`"NodeKind.Z"`, never containing `".Label."`) are **disjoint by construction** — no `NodeKind` string can equal any `Label` string. This is a hard requirement: both backends MUST emit these two exact forms (not `"<ClassName>"` for `NodeKind`), so the two families' canonical-name spaces never overlap and cross-family accidental equality is impossible.

The cross-backend comparison must work **without either backend importing the other**. Mechanism: a duck-typed sentinel. Each label/kind **member** carries its *own* canonical name, readable off the **member instance** (not the type) by any backend reflectively.

**Pinned marker convention (both generators MUST emit exactly this — it is the contract surface):**
- Marker name: **`_fltk_canonical_name`**, an **instance-resolved read returning the member's own canonical string** (e.g. a Python `@property` on the enum, or a per-member value; a `staticmethod`/classmethod is forbidden — it would not be member-specific). The reader does `cn = getattr(other, "_fltk_canonical_name", None)` — read off the **operand instance `other`, never `type(other)`** — so the member identity is intrinsic; no separate call with the member as argument is needed.
- Resolution: `cn is None` → `NotImplemented` (foreign operand); else string-compare `cn` against `self`'s own canonical string.
- This is the **identical** read shape both generators emit. The Rust side (§2.3) does the same `getattr(other, "_fltk_canonical_name")` (a Python attribute access from Rust) and reads the returned string — no Python method *call* to extract it, because the marker resolves to a value/property, not a method needing invocation. Pinning value/property (not method) resolution removes the staticmethod-vs-property ambiguity that would otherwise diverge silently between the two emitters and surface only in the (not-yet-built) cross-backend tests.

- **Python side:** each enum member exposes `_fltk_canonical_name` (its `"<ClassName>.Label.<NAME>"` / `"NodeKind.<MEMBER>"` string). `__eq__` reads it off `other` per the convention above.
- **Rust side:** the `__repr__` string is already the canonical name, but the design pins the key to the explicit `_fltk_canonical_name` marker (a getter exposing the same string), not `repr` (see §2.3 for why a dedicated marker is preferred over `repr`).

A shared, agreed marker name is the contract surface between backends; it is co-generated, so drift is a non-issue (`requirements.md:125`).

**Marker scope (family/node disjointness):** `_fltk_canonical_name` is emitted **only** on `Label` and `NodeKind` enum members — **never on node classes**. Node `__eq__` is unchanged (structural; foreign operand → `NotImplemented`, already gated by `is_instance_of::<ClassName>()` at `gsm2tree_rs.py:431-446`). Every node now carries a `kind` *attribute* (a `NodeKind` member), but the node *object itself* does not expose the marker, so `node == label` reads `getattr(node, "_fltk_canonical_name", None) → None → NotImplemented → False` and never routes a node through the canonical-name path. Implementers MUST NOT add the marker via a shared base/mixin that node classes also inherit.

### 2.2 Python `Label` eq/hash (`gsm2tree.py`)

Emit, per rule's `Label(enum.Enum)`:

- the `_fltk_canonical_name` marker (§2.1): an instance-resolved property/per-member value yielding `"<ClassName>.Label.<NAME>"`. (Generator already knows `class_name` at `gsm2tree.py:112`; compute from `self.name` + a class-level `_fltk_class_name`, or bake a per-member mapping.)
- `__eq__(self, other)`: **same-type fast path first** — `if other is self: return True`; then `if type(other) is type(self): return self.name == other.name` (member-name compare, no canonical-string build), mirroring the Rust own-type fast path (§2.3). This keeps the hot same-backend `children_X` filter (`label == Class.Label.X`, run per child — `gsm2tree.py:201`) off the string-building path, honoring the `requirements.md:126` performance SHOULD ("avoid per-comparison object allocation or string formatting on the same-backend path"). Only the cross-type case falls through to the canonical-string compare: read `cn = getattr(other, "_fltk_canonical_name", None)` **off the operand instance** (§2.1 convention); if `cn is not None` → compare `cn` to `self._fltk_canonical_name` (returns `True`/`False`); else return `NotImplemented`. **Must** return `NotImplemented` (not `False`) for foreign operands so Python invokes the reflected Rust `__eq__` and the `py == rust` direction can reach `True` (`requirements.md:122`). For the equal case at least one side returns `True` as a value — the Python side does (`requirements.md:69` caveat).
- `__hash__(self)`: `hash(canonical_string)`. Moves in lockstep with `__eq__` (`notes-design-user.md:8`).
- `__ne__`: omit; Python derives it from `__eq__` (negation, with `NotImplemented` handled symmetrically). Verified behaviorally (§5 harness): `!=` returns the correct boolean for all cases including `None`/int/str.

**Empirical validation:** a standalone harness (two structurally-identical but distinct `enum.Enum` classes with these overrides) produced: cross-type `==` `True` both directions; diff-name `False`; `== None/1/"str"` all `False`; hash collapse to one set entry; cross-type membership `True`; same-backend self-eq `True`, distinct `False`. All of AC1–AC7 hold for the Python↔Python-foreign-type case, which is the structural twin of Python↔Rust. (The harness exercised the cross-type path; the same-type fast path added above is `enum.Enum`'s own identity/name semantics restated, so it preserves same-backend results by construction — pinned by AC3 and the existing same-backend filter tests, §3.7.)

**Filter compatibility (AC11):** generated `children_X` filters do `label == Class.Label.X` (`gsm2tree.py:201`, e.g. `fltk_cst.py:35`). With the new `__eq__`, same-backend `label == Class.Label.X` takes the same-type fast path (`other is self` / member-name compare) and returns the same result as identity did (the stored label *is* that member). Cross-backend equality is purely additive; no same-backend filter outcome changes. Confirmed in harness.

> `enum.Enum` subclass `__eq__`/`__hash__` override is permitted and behaves as expected (harness used exactly this). No `IntEnum`, no value coercion (`requirements.md:37`).

### 2.3 Rust `Label` eq/hash (`gsm2tree_rs.py`)

PyO3 0.23 (`Cargo.toml:15`) **forbids** combining `#[pyclass(eq)]`/`#[pyclass(hash)]` (each generates a slot — `eq` → `tp_richcompare`, confirmed `pyo3-macros-backend-0.23.5/src/pyclass.rs:422-429`) with a hand-written `__eq__`/`__hash__` in `#[pymethods]` — conflicting slot definitions are a compile error. Therefore:

- **Drop `eq, hash` from the `#[pyclass(...)]` attribute** (`gsm2tree_rs.py:152`); keep `frozen` and the `name`/`pyo3(name=...)` mappings. Keep `#[derive(Clone, PartialEq, Eq, Hash)]` (still useful for Rust-internal use and `into_pyobject`), but it no longer drives the Python slots.
- **Hand-write** in the enum's `#[pymethods]` block (`gsm2tree_rs.py:164-174`, alongside `__repr__`):
  - `__eq__(&self, py, other: &Bound<PyAny>) -> PyResult<PyObject>` — **a plain `__eq__`, matching the validated in-codebase precedent** (`gsm2tree_rs.py:431-446`, the node `_eq_method`), **not** a `__richcmp__`-with-`CompareOp`. Rationale: no requirement covers ordering (`<`/`<=`/…) on labels — AC1–AC11 only exercise `==`/`!=`/hash/membership (`requirements.md:91-98`). Python derives `!=` automatically from `__eq__`; ordering operators simply remain absent (Python raises `TypeError` on `label < label`, which no requirement forbids). A plain `__eq__` is less code and is the *validated* slot shape (`__richcmp__`/`CompareOp` appears **nowhere** in `src/*.rs` — grep, 0 hits — so it is unvalidated in this codebase). Logic: own-type fast path (same Rust enum → direct variant `PartialEq`, no string build); foreign path does `getattr(other, "_fltk_canonical_name")` (§2.1 pinned marker — an attribute/property read, **not** a method call) and compares the returned string to `self`'s canonical string; marker absent (foreign-but-not-a-label/kind) → return `py.NotImplemented()` (Python then tries reflected, ultimately `False`; never raises — `requirements.md:69`).
  - `__hash__(&self) -> isize`: build a `PyString` from the canonical name and return its CPython hash via `PyAnyMethods::hash` (confirmed present in PyO3 0.23.5, `pyo3/src/types/any.rs:860`). This routes the Rust hash through the *same* CPython hashing the Python side uses, guaranteeing `hash(py.X) == hash(rust.X)` within a process. A Rust-native hasher would **not** match: Python's `hash(str)` is salted (PYTHONHASHSEED) per process, a Rust `DefaultHasher` is not. See Edge case §3.1.
- The own-type fast path keeps the hot same-backend filter path (`children_X` calls `.eq(&label_obj)`, `gsm2tree_rs.py:355`) cheap: variant compare, no string build. Cross-backend path is O(canonical-name length) (`requirements.md:126`).

**Canonical-name extraction from a foreign Rust label:** prefer the dedicated `_fltk_canonical_name` marker (§2.1) over `repr()` parsing — `repr()` for nodes is `ClassName(span=..., children=...)` (`gsm2tree_rs.py:458-464`), so a bare `repr`-based key would be ambiguous if ever applied beyond labels. The label `__repr__` *is* the canonical string today, but the design pins the key to the explicit marker (attr/property both backends expose) so the contract is not accidentally coupled to `repr` formatting (resolves the §6.2 repr question independently).

### 2.4 `NodeKind` enum + `kind` discriminant

New, distinct axis from `Label` (`notes-design-user.md:12`): `Label` = a child's role within a parent; `NodeKind` = a node's own type.

- **One `NodeKind` enum per grammar**, one member per rule/node class (`ITEM`, `TERM`, `GRAMMAR`, …). Member name = uppercased rule name (or the node class name uppercased — must be stable and 1:1 with node classes; choose the rule-name-derived form consistent with `class_name_for_rule_node`). Canonical name = **`"NodeKind.<MEMBER>"`** (pinned in §2.1; emit this exact form identically on both backends — disjoint from the `Label` family by construction). This enum gets the **same** cross-backend eq/hash treatment as `Label` (§2.2/§2.3) — it is the second family in `notes-design-user.md:5`.
- **Per-node discriminant:** every node carries `kind`. 
  - Python concrete (`fltk_cst.py`): an **instance attribute** (dataclass field) `kind: typing.Literal[NodeKind.<Rule>] = NodeKind.<Rule>`. **MUST NOT be `ClassVar`** — pyright (1.1.402) rejects a `ClassVar` concrete attribute against the instance-attribute Protocol member with `error: "kind" is not defined as a ClassVar in protocol (reportArgumentType)`, breaking `fltk_cst` ⊨ `cst.CstModule` (the `_DEFAULT_CST` cast at `fltk2gsm.py:18` and every `CstModule`-typed consumer). The instance-attr form verifies clean (0 errors). Side effects of the dataclass field (intended, harmless): joins `__init__` as a keyword arg with a default — parser builds nodes via `node_type()` with no args (`gsm2parser.py:448`), so construction is unaffected — and joins dataclass `__eq__`, where it is always equal within a node type. Do not "optimize" this to `ClassVar`. The Protocol declares `kind: typing.Literal[NodeKind.<Rule>]` (instance attr) so unions narrow.
  - Rust: a `#[getter] fn kind(&self) -> NodeKind` (or a `#[classattr]`) returning the node's member.
  - Protocol (`fltk_cst_protocol.py`): each node Protocol declares `kind: typing.Literal[NodeKind.<Rule>]`.
- **Where `NodeKind` lives:** a single module-level enum in the generated CST module (and a Rust enum exposed Python-side). The Protocol module imports/refers to it. It must be module-level (not nested per node) so `Literal[NodeKind.Item]` is referenceable across node Protocols.

**Pyright narrowing — validated, with a scope limit.** A pyright run (`pyright 1.1.402`) on two node Protocols `Item | Term`, both carrying `kind: Literal[NodeKind.X]`, with a `if node.kind == NodeKind.ITEM:` guard narrowed correctly in both branches (revealed `Item`; 0 errors). Narrowing via `==` on a `Literal[enum-member]` discriminant **is supported for unions of homogeneous `kind`-bearing node Protocols**. **Scope limit (verified):** the guard does **not** work when the union includes a non-`kind`-bearing member such as `Span` — `item.kind` over `Item | Trivia | Span` errors (`Cannot access attribute "kind" for class "Span"`) and `Span` is not eliminated from the narrowed branch. That case (the real `visit_items` site) uses `typing.cast` instead (§2.5).

> **Union-narrowing caveat (`notes-design-user.md:19`):** the `kind`-guard narrows only over unions of **homogeneous node Protocols** (all members `kind`-bearing). When one *label* maps to multiple node types (`Union[Bar, Quux]` under one label — `isinstance-vs-label-investigation.md:204`), `children_<label>()` returns such a homogeneous union; the consumer narrows *within* it via `child.kind == NodeKind.Bar`. The `kind` discriminant is exactly the tool for this. It does **not** apply where a union mixes nodes with the non-node `Span`/`Trivia` slot — pyright errors on `.kind` access against `Span` (verified, §2.5). Does not arise at the current `fltk2gsm.py` blocker sites (the `ITEM` label is 1:1 with `Item` — `isinstance-vs-label-investigation.md:26`; and the `visit_items` union includes `Span`, so `cast` is used there per §2.5), but the mechanism generalizes to out-of-tree homogeneous-union consumers.

> **Scope note:** `NodeKind`/`kind` is a user-settled framework feature (`notes-design-user.md:2,11-13`), delivered this cycle as **forward infrastructure** for out-of-tree homogeneous-union narrowing — **not** as the AC10 mechanism. The in-tree AC10 demonstration (`self.cst` removal) routes around `kind` via `typing.cast` at `visit_items` (§2.5), because that site's union includes the non-node `Span`. Consequently `kind` codegen has **no exercised in-tree consumer this cycle**; its only validation is the dedicated `NodeKind` cross-backend matrix + pyright fixture (§4). Implementers/reviewers must not assume the `test_*_rust_equals_python` parity tests cover `kind` — they do not.

### 2.5 `self.cst` removal from `fltk2gsm.py`

End state: `self.cst` absent; file compares against static constants from a single fixed module (`requirements.md:32`). Concretely:

- **Import a fixed CST module** for constants — the Python CST (`from fltk.fegen import fltk_cst as cst`), used only for `cst.Items.Label.*`, `cst.Disposition.Label.*`, `cst.Quantifier.Label.*` constants. These are cross-backend-equal (§2.2), so comparisons against a Rust-backend-stored label return correct results (AC9).
- **Label comparisons** (`fltk2gsm.py:52-56,58,60,69,71-76,80,122-126,133-137`): rewrite `self.cst.X.Label.Y` → `cst.X.Label.Y`.
- **`isinstance(item, self.cst.Item)` sites** (`fltk2gsm.py:69,80`): **delete the isinstance conjunct.** Per `isinstance-vs-label-investigation.md:26-29`, `item_label == cst.Items.Label.ITEM` is a total equivalence with `isinstance(item, Item)` (label `ITEM` is only ever appended via `append_item(child: Item)`), so the isinstance is pure defensive redundancy. The co-located label check fully replaces it. The `notes-design-user.md:15` steer endorses dropping these "they carry no information the label/kind doesn't." Deleting the `isinstance` conjunct also removes the static narrowing it gave pyright for the subsequent `self.visit_item(item)` argument. **Restore that narrowing with `typing.cast` at these two sites — NOT a `kind`-guard.** The `item` at `visit_items` (`fltk2gsm.py:68,79`) is destructured from `items.children`, statically typed `Item | Trivia | Span` (`fltk_cst_protocol.py:102`). `Span` (`terminalsrc.py:8`) is a hand-written dataclass with **no `kind` attribute** and is not generator-emitted, so it never gains one. **Empirically confirmed (pyright 1.1.402):** writing `item.kind == NodeKind.ITEM` over `Item | Trivia | Span` produces `error: Cannot access attribute "kind" for class "Span"` and does *not* eliminate `Span` from the narrowed branch (revealed `Item | Span`), so the body access also errors. The correct fix at these sites is `item = typing.cast("cst.Item", item)` (verified: 0 pyright errors). The `kind`-guard pattern (§2.4) is reserved for unions of **homogeneous node Protocols** (`Item | Term`, all `kind`-bearing — verified narrows cleanly); it is structurally unavailable where the union includes the non-node `Span`. The `cast` needs no `self.cst` (it targets the `TYPE_CHECKING` Protocol type), so no `self.cst` residue results — the AC10 full-removal escape (`requirements.md:103`) stays closed.
- **Constructor parameter `cst=`** (`fltk2gsm.py:22`): see Open question §6.5 — drop / ignore / retain-as-noop. **Decision (settled): drop the parameter entirely.** No in-tree caller passes `cst=` for a non-default backend in a way that survives this change (the whole point is the file is now backend-agnostic). External callers constructing `Cst2Gsm(terminals, cst=...)` are affected; this is intended in-scope per `requirements.md:120`.
- The `_DEFAULT_CST`/`_default_cst` sentinel scaffolding (`fltk2gsm.py:13-18`) and the `TYPE_CHECKING` Protocol import become unnecessary for dispatch but the **Protocol annotations on visit methods** (`cst.Grammar`, `cst.Rule`, …) should remain for typing — keep the `if TYPE_CHECKING: import fltk_cst_protocol as cst` for *annotations*, and use a *separate* concrete import (e.g. `from fltk.fegen import fltk_cst as _cst_const`) for the runtime constants, to avoid a name clash between the Protocol-typing `cst` and the constant-bearing module. (Name choices are implementation detail; the constraint is: annotations stay Protocol-typed, constants come from one concrete module.)

`bootstrap2gsm.py` already uses a concrete module (`cst.Items.Label.*`, no `self.cst`); its identical isinstance redundancy (`isinstance-vs-label-investigation.md:35-38`) is **out of scope** here (not required by AC10) but noted as a parallel cleanup candidate.

### 2.6 Files touched

- `fltk/fegen/gsm2tree.py` — emit Python `Label` `__eq__`/`__hash__`/canonical marker; emit `NodeKind` enum (+ its eq/hash); emit `kind` on each node; emit `kind` + `NodeKind` refs in the Protocol module.
- `fltk/fegen/gsm2tree_rs.py` — drop `eq,hash` from label pyclass; emit hand-written `__eq__`/`__hash__`/canonical marker on label enums; emit `NodeKind` Rust enum with the same; emit `kind` getter on each node struct; register the `NodeKind` class.
- **Regenerated outputs** (per CLAUDE.md regen→`make fix`→commit): `fltk/fegen/fltk_cst.py`, `fltk/fegen/fltk_cst_protocol.py`, `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`. (`tests/rust_cst_fegen/src/cst.rs` is a hand-copied duplicate of `src/cst_fegen.rs` — `TODO(fegen-cst-rs-single-source)`, `exploration.md:226`; keep in sync.)
- `fltk/fegen/fltk2gsm.py` — `self.cst` removal (§2.5).
- New/extended tests (§4).

---

## 3. Edge cases / failure modes

### 3.1 Per-process hash agreement (salted string hash)
Python `hash(str)` is randomized per process (PYTHONHASHSEED). A Rust-side `DefaultHasher` over the same string would **not** match Python's `hash(str)`, breaking AC4 (`hash(py.X)==hash(rust.X)`). **Mitigation:** the Rust `__hash__` builds a `PyString` from the canonical name and returns its CPython hash via `PyAnyMethods::hash` (PyO3 0.23.5, `pyo3/src/types/any.rs:860`), so both sides go through the *same* salted CPython hash and agree within the process. Pinned by the AC4 test (cross-backend, same process).

### 3.2 `NotImplemented` on both sides → wrong `False`
If both sides returned `NotImplemented` for the equal cross-backend case, Python falls back to identity → wrong `False` (`requirements.md:69`). **Mitigation:** the marker-based path means each side, when it recognizes the *other* as a label (via the duck-typed marker), returns a real boolean — not `NotImplemented`. `NotImplemented` is reserved strictly for genuinely-foreign operands. The AC1 test pins both directions.

### 3.3 Foreign operand that *accidentally* exposes the marker name
A non-label object defining the same marker attribute would be treated as a label. **Mitigation:** marker name is namespaced/unlikely (`_fltk_canonical_name`) and returns a string; mismatched strings simply compare unequal. No raise, worst case a `False`. Acceptable; documented. **FLTK's own node objects do not expose the marker** (§2.1 marker-scope), so `node == label` stays `NotImplemented`/`False` — the only accidental-exposure risk is a non-FLTK object, covered here.

### 3.4 `kind` member naming collisions / reserved words
`NodeKind` members derive from rule names; rule names are already validated as identifiers (`gsm2tree_rs.py:57`). Uppercased member names could collide if two rules differ only by case — not possible since rule names are lowercased-and-unique by grammar construction. No new failure mode.

### 3.5 Label-free nodes and `(None, child)` children
Raw `.children` iteration can see `(None, Trivia)` / `(None, Span)` entries (`isinstance-vs-label-investigation.md:128-135`). The `kind` discriminant lives on the **child node**, not the label slot, so a consumer that has a node in hand narrows on `node.kind` regardless of the `None` label. The typed accessors already hide `None`-label entries. With the trivia fix landed (`trivia-divergence-rootcause-v2.md` — Rust parser now matches Python `capture_trivia=False` at base a5cffc5) and typed accessors, this does not surface in `fltk2gsm.py` (`notes-design-user.md:19`). `fltk2gsm.py:48` iterates `items.children` raw, but only to read interleaved `ITEM`/separator labels — separators are `Span` children under non-`None` labels (`NO_WS`/`WS_*`), and trivia is no longer appended on the Python or Rust path post-fix, so the raw iteration sees only labeled entries.

### 3.6 PyO3 derive/slot conflict (compile failure)
If `eq`/`hash` are not removed from `#[pyclass]`, the hand-written `__eq__`/`__hash__` fail to compile (PyO3 conflicting slots). **Mitigation:** §2.3 removes them. The build (`make build-fegen-rust-cst`, `build-native`, `build-test-user-ext`) is the gate; a regression here fails loudly at compile time, not silently.

### 3.7 Same-backend filter regression
Covered by AC11 / §2.2. The own-type fast path in Rust `__eq__` and the same-type fast path in Python `__eq__` (§2.2) both reproduce prior same-backend results. Pinned by existing same-backend tests (`test_phase4_rust_fixture.py:282-295`).

### 3.8 Cross-grammar canonical collision
Two unrelated grammars each defining `Items.Label.NO_WS` compare equal (`requirements.md:51`). Accepted (Open question §6.4 default). No mitigation; documented as intended scope of "same label name."

---

## 4. Test plan

After this cycle the following tests exist (TDD: write failing first).

**Cross-backend label equality (new test module, e.g. `tests/test_cross_backend_label_equality.py`):** parametrized over backend pairs `(py, fegen_rust_cst)` and `(fltk._native.fegen_cst, fegen_rust_cst)`:
- **AC1/AC2/AC3:** `py.Items.Label.NO_WS == rust...NO_WS` both directions `True`; vs `WS_ALLOWED` `False`/`!=` `True`; same-backend self-eq and distinct-ineq.
- **AC4:** `hash(py.X) == hash(rust.X)` (same process) for several members.
- **AC5:** `len({py.X, rust.X}) == 1`; `rust.X in {py.X}`; dict keyed by one retrieved by the other.
- **AC6:** `rust.X in (py.X, py.Y)` `True`.
- **AC7:** `py.X == None|1|"Items.Label.NO_WS"|object()|rust.Disposition.Label.INCLUDE` all `False`, `!=` `True`, no raise; symmetric (`None == py.X` etc.).
- **AC8:** AC1/AC4/AC6 with `fltk._native.fegen_cst` ↔ `fegen_rust_cst`.

**NodeKind equality + narrowing:**
- Same cross-backend matrix for `NodeKind` members (eq/hash/membership) — it shares the §2.1 contract.
- A pyright-checked fixture (in-tree, type-checked by `make check`) exercising `if node.kind == NodeKind.Item: <Item-only access>` over a **homogeneous** `Union[Item, Term]` (all `kind`-bearing), proving narrowing. (The §2.4 harness becomes a committed typing test.) The fixture must **not** use a `Span`-bearing union — that is the verified-failing case (§2.5) and is handled by `cast`, not the `kind`-guard.

**`fltk2gsm.py` / AC9 / AC10:**
- A focused test: a label held from backend A compares equal and is `in`-found against the fixed-module constant (AC9).
- `grep`-style or import assertion that `self.cst` no longer appears in `fltk2gsm.py` (AC10), plus that `Cst2Gsm` has no `cst` parameter (if §6.5 → drop).
- Existing `test_phase4_fegen_rust_backend.py` parity (`python_result == rust_result`) continues to pass **without** `self.cst` injection driving dispatch (`requirements.md:102`).

**Regression / same-backend:** existing `test_phase4_rust_fixture.py` (AC5 API contract, per-backend eq/hash), `test_fegen_rust_cst.py`, `test_rust_cst_poc.py`, and full `uv run pytest` stay green. `make check` (ruff + pyright) passes on regenerated code after `make fix`.

---

## 5. Empirical validation performed (base a5cffc5 / working tree)

- **Python cross-type eq/hash:** standalone harness with two distinct `enum.Enum` classes carrying canonical-name `__eq__`/`__hash__` → AC1–AC7 behaviors all correct (symmetry, `NotImplemented` fallback, string rejection, hash collapse, membership). Confirms §2.2.
- **Pyright narrowing:** `pyright 1.1.402`. (a) `kind: Literal[NodeKind.X]` over homogeneous `Item | Term` with `==` guard → 0 errors, both branches narrowed (`Item`). (b) **Same guard over `Item | Trivia | Span` (the real `visit_items` union) → 2 errors** (`Cannot access attribute "kind" for class "Span"`; `Span` survives the branch). (c) `typing.cast("cst.Item", item)` over the `Span`-bearing union → 0 errors. Confirms §2.4 narrowing holds **only** for homogeneous node unions, and §2.5's `cast` (not `kind`-guard) is correct at `visit_items`.
- **PyO3 version:** 0.23 (`Cargo.toml:15`); `#[pyclass(eq, hash)]` present on all label enums (`src/cst_fegen.rs:16`, three crates). Confirms the derive must be dropped to hand-write `__eq__` (§2.3) — PyO3 forbids both. The node-level hand-written `__eq__` already in the generator (`gsm2tree_rs.py:431-446`, a plain `fn __eq__(&self, py, other: &Bound<PyAny>) -> PyResult<PyObject>` returning `py.NotImplemented()` for foreign operands) demonstrates **exactly the slot shape §2.3 now prescribes** for labels compiles in this codebase. (`__richcmp__`/`CompareOp` is *not* used anywhere in `src/*.rs` — grep, 0 hits — which is why §2.3 adopts the plain-`__eq__` shape rather than `__richcmp__`.)
- **`fltk2gsm.py` isinstance redundancy:** confirmed `ITEM` label ↔ `Item` type is 1:1 (`fltk_cst.py` `append_item`), so the two `isinstance` conjuncts are deletable (§2.5).

Not yet built/run (deferred to implementation): the actual Rust label `__eq__`/`__hash__` compile, and the per-process hash agreement (§3.1) — in particular the **AC8 two-crate** case (`fltk._native.fegen_cst` ↔ `fegen_rust_cst`, distinct cdylib crates linking the same abi3 CPython): both crates routing `__hash__` through `PyString::hash` will agree in-process, but this is **unproven without a built test** (the §3.1 argument is framed py↔rust). Pin AC8 hash equality with an actual cross-crate test early; do not infer it from the py↔rust argument alone. Both are gated by the build and the AC4/AC8 tests; flagged.

---

## 6. Resolved decisions (user-settled 2026-06-05)

All five below are SETTLED — not open. Each resolution is the design's proposed default. The "Redirect" note records what to change if the user later reverses a call.

1. **`canonical_name` public property.** Expose `label.canonical_name` / `kind.canonical_name` as committed API, or keep the marker internal (`requirements.md:132`)? **Decision (settled): internal marker only** (Option A) — the marker stays the underscore-prefixed `_fltk_canonical_name` (§2.1), not a documented public surface. The marker must exist regardless; this is purely whether it is *also* exposed under a public name. Redirect: user says "expose `.canonical_name`" → add a public `canonical_name` property (aliasing the same string) on both backends and both enum families.

2. **Python `repr`/`str` alignment.** Change Python `repr`/`str` to `"Items.Label.NO_WS"` to match Rust (`requirements.md:137`)? **Decision (settled): leave Python default repr unchanged** (Option A); eq/hash is the contract, and §2.3 deliberately decouples the key from `repr`. Redirect: "make reprs match" → emit a `__repr__` on the Python `Label`.

3. **String-equality convenience (AC7).** `label == "Items.Label.NO_WS"` returns `False` today by spec (`requirements.md:142`). **Decision (settled): keep `False`** (string-coercion footgun, mirrors IntEnum rejection). Redirect: "allow string comparison" → both eq sides accept a matching string and AC7/§System-behavior update.

4. **Cross-grammar collision.** Canonical name is rule+label scoped, no grammar identity (`requirements.md:146`). **Decision (settled): accept collision** (a single process rarely mixes two grammars' CSTs; where it does, identical canonical names genuinely denote "the same label name"). Redirect: "must disambiguate by grammar" → canonical name gains a grammar-id component on both families.

5. **`Cst2Gsm.__init__` `cst=` parameter fate** (`requirements.md:110`). **Decision (settled): drop the parameter.** Alternatives: ignore (accept+discard) or retain as no-op for source-compat. Dropping is cleanest and matches "self.cst absent"; retaining a no-op preserves external `Cst2Gsm(terminals, cst=...)` call sites. Redirect: user says "keep a no-op param for compat" → retain `cst=None` ignored.

---

**Verdict:** APPROVED (review chain, judge-verdict-design.md) · all §6 decisions settled · ready for implementation (pending user go-ahead).
