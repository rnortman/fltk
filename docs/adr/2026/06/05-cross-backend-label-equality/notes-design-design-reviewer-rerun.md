# Design review (rerun) — cross-backend-label-equality/design.md

Adversarial re-review against requirements.md, exploration.md, source at base b55e212.
Verified line-number citations, PyO3 internals, and pyright behavior directly.
Most load-bearing claims hold. Findings below.

---

## design-1 — `kind: ClassVar` on concrete node will NOT satisfy the generated Protocol (verified pyright failure)

**Section:** §2.4 "Per-node discriminant → Python concrete (`fltk_cst.py`): a class-level `kind: typing.ClassVar[...] = NodeKind.<Rule>` (**or instance attr**)"; Protocol declares `kind: typing.Literal[NodeKind.<Rule>]` (instance attr).

**What's wrong:** The design offers `ClassVar` as the *first/example* form for the concrete node's `kind`, while the Protocol (§2.4: "each node Protocol declares `kind: typing.Literal[NodeKind.<Rule>]`") declares it as an **instance attribute**. pyright rejects a `ClassVar` concrete attribute against an instance-attribute Protocol member.

**Why (source-backed):** Reproduced directly with pyright 1.1.402 (the design's own tool version):
- Concrete `kind: ClassVar[Literal[NodeKind.ITEM]] = NodeKind.ITEM` vs Protocol `kind: Literal[NodeKind.ITEM]` →
  `error: "kind" is not defined as a ClassVar in protocol (reportArgumentType)` — concrete class is **not** assignable to the Protocol.
- Concrete `kind: Literal[NodeKind.ITEM] = NodeKind.ITEM` (instance-attr / dataclass field) vs same Protocol → **0 errors**.
The concrete CST nodes are `@dataclasses.dataclass` (`fltk_cst.py:8-9`) and the generated `CstModule` Protocol structurally requires every node to satisfy its node Protocol; today fltk2gsm.py relies on that (`fltk2gsm.py:18` casts `fltk_cst` to `cst.CstModule`). The Protocol member cannot itself be `ClassVar` because §2.4/the narrowing requires `Literal[NodeKind.Item]` as a discriminant on the union members (a `ClassVar` discriminant is not what was validated, and would change the narrowing fixture).

**Consequence:** If the implementer picks the `ClassVar` form (presented first as "Cleanest"-style example), `make check` pyright fails on the regenerated `fltk_cst.py` not satisfying `fltk_cst_protocol.py` — a hard gate failure, and the `fltk2gsm.py` `_DEFAULT_CST` cast / any `CstModule`-typed consumer breaks. The design presents both forms as interchangeable ("or instance attr") when only one passes.

**Fix:** Pin the concrete Python `kind` to an **instance attribute** (dataclass field with default `= NodeKind.<Rule>`), not `ClassVar`. Note the side effect: as a dataclass field it joins `__init__` (keyword, has default — parser builds nodes via `node_type()` with no args, `gsm2parser.py:448`, so construction is unaffected) and dataclass `__eq__` (harmless: always equal within a node type). State this explicitly so the implementer does not "optimize" it back to `ClassVar`.

---

## design-2 — Marker mechanism underspecified: type-level lookup vs per-member value (self-inconsistent)

**Section:** §2.1 "a `_fltk_canonical` staticmethod … that maps a member to its string"; §2.2 "`__eq__` reads `getattr(type(other), "_fltk_canonical", None)`; if absent → `NotImplemented`; else compare strings."

**What's wrong:** §2.2 reads the marker off `type(other)` (a class-level staticmethod) and then "compare strings" — but a class-level staticmethod does not by itself yield *the specific member's* canonical string; it must be **invoked with the operand member** (`marker(other)`), or the marker must be read off the **instance** (`getattr(other, ...)` resolving to a property/bound value). The text conflates a type-level lookup with a member-level value and omits the call/resolution step. §2.1 ("maps a member to its string") and §2.2 ("reads `getattr(type(other), …)` … else compare strings") describe two different calling conventions.

**Why:** Cross-backend eq needs `canonical_name(other_member)`. Python `enum` members share one type; `getattr(type(other), "_fltk_canonical")` returns one staticmethod for all members, so the member identity must be passed in or the attribute must be instance-resolved. The design never says which. The Rust side (§2.3, `other: &Bound<PyAny>`) has the same ambiguity: it must `getattr` the marker and **call** it (a Python call from Rust) to extract a foreign Python label's string — the design says only "reads the operand's canonical name via the same duck-typed marker."

**Consequence:** Implementer-facing ambiguity at the exact contract surface between the two generators. A staticmethod-not-called vs property mismatch between the Python and Rust emitters yields `NotImplemented`/`AttributeError` at runtime and silently-`False` cross-backend equality — defeating AC1/AC8 — and would only surface in the cross-backend tests (which §5 admits are not yet built). Co-generation does not save you if the two sides assume different conventions.

**Fix:** Pin one convention explicitly, e.g. an **instance-resolved** read: `cn = getattr(other, "_fltk_canonical_name", None)` where each member exposes its own canonical string (property or per-member value); `None` → `NotImplemented`; else string-compare. Specify the *identical* read+invoke shape both generators must emit, and (if a method) the exact signature Rust must call.

---

## design-3 — `_fltk_canonical` marker resolved via `getattr(other, …)` collides with the existing `kind` attribute family / cross-family read path is unstated

**Section:** §2.1 "Family disjointness"; §2.4 (`NodeKind` shares the §2.1 marker path); §2.2 marker read.

**What's wrong:** The design asserts family disjointness purely from canonical-string forms (`"X.Label.Y"` vs `"NodeKind.Z"`). That is sound *for the string compare*. But the marker-read step is shared across both families and across **nodes** too: a node carries `kind` (a `NodeKind` member) and is itself compared in user code. The design never states whether a *node* object exposes `_fltk_canonical` (it must not — nodes are not labels/kinds and node eq is structural, §`_eq_method` gsm2tree_rs.py:431). If the marker name is read off arbitrary operands via duck typing (§3.3 acknowledges accidental exposure), the design should confirm that `NodeKind` members, `Label` members, and `kind`-bearing **nodes** are kept distinct: only the two enum families expose the marker; nodes do not.

**Why:** §3.3 only addresses a *non-FLTK* object accidentally defining the marker. It does not address FLTK's own node objects, which now all carry a `kind` enum and participate in user `==`. A node `n == someLabel` must remain `False`/`NotImplemented` and never accidentally route through the canonical-name path.

**Consequence:** If node codegen ever exposed the marker (e.g. via an over-broad shared mixin), `node == label` could become structurally confused. Low likelihood given separate codegen, but unstated — a reviewer cannot confirm the invariant holds. Left implicit, an implementer adding the marker via a shared base could violate it.

**Fix:** State explicitly: the `_fltk_canonical*` marker is emitted **only** on `Label` and `NodeKind` enum members, never on node classes; node `__eq__` is unchanged (structural, foreign → `NotImplemented`).

---

## Verified-correct (no finding; recorded to bound the review)

- §1.1/§2.3 PyO3 slot conflict: `#[pyclass(eq)]`→richcmp slot, `#[pyclass(hash)]`→hash slot — confirmed `pyo3-macros-backend-0.23.5/src/pyclass.rs:419-431`. Dropping `eq, hash` to hand-write is required. ✓
- §2.3/§3.1 `PyAnyMethods::hash` exists in PyO3 0.23.5 (`any.rs:860`); routing Rust `__hash__` through `PyString::hash` to match salted CPython hash is grounded. ✓
- §5 node `_eq_method` precedent: `gsm2tree_rs.py:431-446` is a plain `fn __eq__(&self, py, other: &Bound<PyAny>) -> PyResult<PyObject>` returning `py.NotImplemented()`; node pyclass is bare `#[pyclass]` (line 192) — the prescribed label slot shape compiles in-tree. ✓
- §2.4 pyright narrowing on homogeneous `Item | Term` via `kind == NodeKind.X` with instance-attr `Literal[...]` discriminant — reproduced, 0 errors, both branches narrow. ✓
- §2.5 `visit_items` union is `Item | Trivia | Span` — confirmed `fltk_cst_protocol.py:102`; `Span` is hand-written (`terminalsrc`) with no `kind`; `cast("cst.Item", item)` is the correct route. ✓
- §2.5 `self.cst` usage enumeration (52-56,58,60,69,71-76,80,122-126,133-137) is complete — confirmed by grep; no missed site. ✓
- §2.6 files-touched list matches reality (`cst_generated.rs` = POC 2-rule output, `cst_fegen.rs` = fegen.fltkg 14-rule output, both from `RustCstGenerator`; both regen). ✓
- §1.1 label enum generation line cites (gsm2tree.py:112-115; gsm2tree_rs.py:151-160, repr 164-174) accurate. ✓
- §6 decisions are user-settled (notes-design-user.md); not re-litigated. AC7 `== "string"` → False holds under the marker scheme (plain str has no marker → NotImplemented → False). ✓

---

**Net:** design-1 is a concrete gate-failing trap (the offered `ClassVar` form fails pyright); fix the wording to mandate the instance-attr form. design-2/design-3 are specification gaps at the cross-backend marker contract that, unresolved, surface only in the not-yet-built cross-backend tests. No groundedness failures against source; no scope creep beyond user-settled framework features.
