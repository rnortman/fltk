# Narrowing-mechanism empirical probe

Decides how a consumer narrows a CST `child` from `tuple[Label | None, Union[Item, Trivia, Span]]`'s
value half (`Item | Trivia | Span`) to a concrete type, cast-free and suppression-free.

## Environment (actual)

- pyright **1.1.402** (run via `uv run pyright` against the FLTK project venv)
- Python **3.10.20** (the project interpreter — `uv run python`; note bare `python3` on this host is 3.14,
  but every probe below was run under 3.10 via `uv run --project /home/rnortman/src/fltk`)
- typing_extensions **4.14.0** (`TypeIs` source)
- Scratch dir: `/tmp/narrowprobe/` (no production code touched)

All pyright output below is verbatim (WARNING/version-nag lines stripped).

---

## QUESTION A — native discriminated-union narrowing on `.kind`

### A1 — same-enum union (`Item | Trivia`, both `kind: Literal[NodeKind.*]`) — **PASS**

Both `if child.kind == NodeKind.ITEM:` and `match child.kind:` narrow `child` itself (not just `.kind`).

```
/tmp/narrowprobe/qa1.py:30:21 - information: Type of "child" is "Item"     # if-branch
/tmp/narrowprobe/qa1.py:32:21 - information: Type of "child" is "Trivia"   # else-branch
/tmp/narrowprobe/qa1.py:38:25 - information: Type of "child" is "Item"     # match case NodeKind.ITEM
/tmp/narrowprobe/qa1.py:40:25 - information: Type of "child" is "Trivia"   # match case NodeKind.TRIVIA
0 errors, 0 warnings, 4 informations
```

### A2 — THE CRUX: discriminants are Literals from DIFFERENT enums — **PASS**

`Item.kind: Literal[NodeKind.ITEM]`, `Trivia.kind: Literal[NodeKind.TRIVIA]`,
`Span.kind: Literal[SpanKind.SPAN]` (a **separate** enum). pyright STILL narrows `child`:

```
/tmp/narrowprobe/qa2.py:38:21 - information: Type of "child" is "Item"           # if child.kind == NodeKind.ITEM
/tmp/narrowprobe/qa2.py:40:21 - information: Type of "child" is "Trivia | Span"  # else
/tmp/narrowprobe/qa2.py:46:25 - information: Type of "child" is "Item"           # match case NodeKind.ITEM
/tmp/narrowprobe/qa2.py:48:25 - information: Type of "child" is "Trivia"         # match case NodeKind.TRIVIA
/tmp/narrowprobe/qa2.py:50:25 - information: Type of "child" is "Span"           # match case SpanKind.SPAN
0 errors, 0 warnings, 5 informations
```

(Re-run with `--warnings`: identical, 0 errors/warnings.)

**Definitive finding:** pyright's discriminated-union narrowing keys off each member having a *unique
literal* `kind` field; it does **not** require all those literals to come from the same enum type. A
shared, library-level `SpanKind.SPAN` literal on `Span` is therefore **sufficient**. `Span` does **not**
need to be a member of every per-grammar `NodeKind`. No hard coupling between the shared `Span` and the
generated per-grammar enum is required.

Important detail for the `match` form: the cases must be written against the *correct* enum per member
(`case NodeKind.ITEM` ... `case SpanKind.SPAN`). A single `match` can mix cases from both enums and
each narrows correctly.

### A3 — fallbacks — **N/A (A2 passed)**

Not needed, but verified anyway: putting a `SPAN` member on the shared enum and giving `Span.kind:
Literal[NodeKind.SPAN]` (fallback ii) also narrows identically (`qa3.py`, 0 errors, same 5 reveal_types).
So both shapes work; A2 shows the *minimal* one (Span gets its own tiny enum, zero dependency on the
generated `NodeKind`).

### A4 — `kind` field on `frozen=True, slots=True` dataclass — **PASS**

Class-level Literal default on a frozen+slots dataclass works cleanly at runtime:

```
kind: SpanKind.SPAN
frozen check:
  frozen OK: FrozenInstanceError
eq (kind excluded from compare? default is included): True
slots: ('start', 'end', '_source', 'kind')
```

`kind` lands in `__slots__`, the instance stays frozen, and equality still holds (the kind default is
constant so it never breaks `==`). One caveat for the real `terminalsrc.Span`: it has fields with
defaults (`_source`), so `kind` (also defaulted) must be declared **after** them — non-default-after-
default ordering would be a `TypeError` at class creation. In the probe `kind` was placed last.

---

## QUESTION B — `TypeIs` predicate

Predicate body: `getattr(x, "kind", None) == NodeKind.ITEM`, return `TypeIs[Item]`.

### B1 — bidirectional narrowing — **PASS**

```
/tmp/narrowprobe/qb.py:40:21 - information: Type of "child" is "Item"           # positive branch
/tmp/narrowprobe/qb.py:42:21 - information: Type of "child" is "Trivia | Span"  # negative/else branch
```

Both directions narrow as required (positive -> `Item`, negative -> `Trivia | Span`).

### B2 — `typing_extensions.TypeIs` under pyright on 3.10 + subtype constraint — **PASS**

Works under pyright 1.1.402 / Python 3.10.20 / typing_extensions 4.14.0. The TypeIs subtype constraint
(narrowed type must be a subtype of the input type) IS enforced — a deliberately-wrong target errors:

```
/tmp/narrowprobe/qb2.py:25:22 - error: Return type of TypeIs ("Other") is not consistent with value
  parameter type ("Child") (reportGeneralTypeIssues)
```

The valid `TypeIs[Item]` over input `Item | Trivia | Span` produces 0 errors. Constraint satisfied.

### B3 — Span-safety of `getattr(x,"kind",None)` at runtime — **PASS**

With `Span` having NO `kind` attribute (frozen+slots), the predicate is safe:

```
is_item(Span): False
is_item(Item): True
is_item(Trivia): False
```

`getattr(span, "kind", None)` returns `None`, `None == NodeKind.ITEM` is `False`. No `AttributeError`.

### B4 — `assert is_item(item)` narrows with NO cast — **PASS**

```
/tmp/narrowprobe/qb.py:47:17 - information: Type of "item" is "Item"
```

After `assert is_item(item)`, `item` is `Item` with no `typing.cast`.

---

## QUESTION C — cross-backend reality check

### C1 — Rust nodes expose `kind` — **PASS (kind getter exists)**

`fltk/fegen/gsm2tree_rs.py` emits, for every node class, a `#[getter] fn kind(&self) -> NodeKind`
(method `_kind_getter`, lines 349-358) returning the node's `NodeKind` member, plus a module-level
`#[pyclass(name = "NodeKind")]` enum (`_node_kind_block`, lines 181-222). So a Rust-produced node
exposes `node.kind` as a Python attribute returning a `NodeKind` instance.

- A duck-typed `getattr(x, "kind", None) == NodeKind.ITEM` predicate body **works against Rust nodes**:
  `getattr` reads the getter, and the Rust `NodeKind.__eq__` is explicitly cross-backend (it compares via
  `_fltk_canonical_name`, `_emit_rust_cross_backend_eq_hash`, lines 150-179), so `==` against the
  Python-backend `NodeKind` member agrees across backends.
- The Rust `Span` is opaque (`span: PyObject`, no Rust-level typed Span; preamble TODO at lines 119-121
  confirms span is intentionally opaque today). So a Rust node's `kind` getter never collides with Span,
  and the `getattr(...None)` Span-miss path holds on the Rust side too.

For the **native `match`/`if` mechanism (Question A)**, what matters is the *static* annotation surface,
not the runtime backend: as long as the generated `.pyi`/stub declares `kind: Literal[NodeKind.X]` per
node and `Span.kind: Literal[SpanKind.SPAN]`, pyright narrows regardless of whether the instance came
from Python or Rust at runtime.

---

## BOTTOM LINE

**Native `match child.kind` / `if child.kind == ...` IS achievable — it is the recommended mechanism.**

The feared blocker (Span can't share the per-grammar generated `NodeKind`) is a non-issue: A2 proves
pyright narrows a discriminated union even when members' `kind` literals come from *different* enums.

Exact minimal `Span` change (`fltk/fegen/pyrt/terminalsrc.py`):

1. Add a shared, library-level enum, e.g.
   ```python
   class SpanKind(Enum):
       SPAN = "SPAN"
   ```
2. Add one field to `Span` (after the existing defaulted `_source`, to respect default-ordering):
   ```python
   kind: Literal[SpanKind.SPAN] = SpanKind.SPAN
   ```
   This is compatible with `frozen=True, slots=True` (A4), keeps `==` intact, and adds no dependency on
   any generated per-grammar `NodeKind`.

Consumers then write cast-free, suppression-free:
```python
match child.kind:
    case NodeKind.SOME_RULE: ...   # child: SomeRule
    case SpanKind.SPAN: ...        # child: Span
```

`TypeIs` (Question B) is fully viable as a secondary/ergonomic helper (all of B1-B4 PASS, and it is the
right tool for the `assert is_item(item)` fltk2gsm usage), but it is **not required** to get cross-backend,
cross-enum narrowing — native discrimination already delivers it. Recommend native `.kind` discrimination
as the primary mechanism, with optional generated `TypeIs` predicates for assert-style call sites.

Cross-backend: Rust nodes already expose a `kind` getter returning a cross-backend-`__eq__` `NodeKind`,
so both mechanisms work identically against Python- and Rust-backed nodes.

---

## FOLLOW-UP — dispatch via `cst.<Node>.kind` class-attribute references (no enum namespace)

Same union `Item | Trivia | Span`; each `kind` is a dataclass field with a Literal default
(`Item.kind: Literal[NodeKind.ITEM] = NodeKind.ITEM`, `Trivia.kind: Literal[NodeKind.TRIVIA]`,
`Span.kind: Literal[SpanKind.SPAN]` — separate enum). Scratch: `/tmp/narrowprobe/qd.py`.
pyright 1.1.402 / Python 3.10.20. Verbatim output:

```
/tmp/narrowprobe/qd.py:37:13 - information: Type of "Item.kind" is "Literal[NodeKind.ITEM]"
/tmp/narrowprobe/qd.py:38:13 - information: Type of "Span.kind" is "Literal[SpanKind.SPAN]"
/tmp/narrowprobe/qd.py:45:25 - information: Type of "child" is "Item"     # match case Item.kind
/tmp/narrowprobe/qd.py:47:25 - information: Type of "child" is "Trivia"   # match case Trivia.kind
/tmp/narrowprobe/qd.py:49:25 - information: Type of "child" is "Span"     # match case Span.kind
/tmp/narrowprobe/qd.py:56:25 - information: Type of "child" is "Item"     # baseline match case NodeKind.ITEM
/tmp/narrowprobe/qd.py:58:25 - information: Type of "child" is "Trivia"
/tmp/narrowprobe/qd.py:60:25 - information: Type of "child" is "Span"
/tmp/narrowprobe/qd.py:66:21 - information: Type of "child" is "Item"     # if child.kind == Item.kind
/tmp/narrowprobe/qd.py:68:21 - information: Type of "child" is "Trivia"   # elif child.kind == Trivia.kind
/tmp/narrowprobe/qd.py:70:21 - information: Type of "child" is "Span"     # elif child.kind == Span.kind
0 errors, 0 warnings, 11 informations
```

### D1 — `match child.kind:` with class-attribute **value patterns** (`case Item.kind:`) — **PASS**

`case Item.kind:` is a dotted-name value pattern. pyright compares against the Literal value AND narrows
the OUTER `child` (Item / Trivia / Span respectively). Behavior is **identical to the enum-member baseline**
`case NodeKind.ITEM:` (lines 56-60 narrow the same way). No difference.

### D2 — `if child.kind == Item.kind:` (class-attribute on RHS) — **PASS**

The class-attribute reference on the RHS narrows `child` in each `if`/`elif` arm (Item / Trivia / Span).

### D3 — hide the enum namespace entirely — **PASS**

Both forms (`match` and `if`) dispatch and narrow using ONLY `cst.<Node>.kind` class-attribute references.
The consumer never names `NodeKind` or `SpanKind`. The enum namespace is fully hideable from consumer code.

### D4 — `.kind` on the CLASS yields the Literal value with right type — **PASS**

`reveal_type(Item.kind)` -> `Literal[NodeKind.ITEM]`; `reveal_type(Span.kind)` -> `Literal[SpanKind.SPAN]`.
A dataclass field with a Literal default is readable on the class object and keeps the narrow Literal type
(not widened to the bare enum). This is what makes the value-pattern dispatch work.

### Follow-up bottom line

A consumer CAN dispatch and narrow using only `cst.<Node>.kind` class-attribute references — via BOTH
`match` (value patterns `case Item.kind:`) and `if`/`elif` (`child.kind == Item.kind`) — with no mention
of any `NodeKind`/`SpanKind` enum. The generated enum namespace is an implementation detail that can stay
hidden from downstream code; nodes need only expose `<Node>.kind` as a Literal-typed class attribute.

---

## CROSS-BACKEND — equality through a `match` value pattern (real bridge)

Uses the REAL `fltk.fegen.fltk_cst.NodeKind` (concrete Python backend) whose members carry
`_fltk_canonical_name` and the canonical-name bridge `__eq__` (fltk_cst.py:25-36, returns
`NotImplemented` for foreign operands). A protocol-only consumer compares a concrete instance's `.kind`
against a *different* object (the protocol module's `cst.<Node>.kind`) carrying the same canonical name.
Scratch: `/tmp/narrowprobe/qe.py`. Runtime output (Python 3.10.20):

```
=== E1: bridge equality both orders ===
concrete == Proto.items : True
Proto.items == concrete : True
concrete == Proto.item  : False
Proto.item == concrete  : False
=== E2: match value-pattern routing across types ===
match concrete (ITEMS): ITEMS
match NodeKind.ITEM   : ITEM
match NodeKind.TERM   : NONE
=== E3: operand order — subject.__eq__ vs pattern.__eq__ ===
MATCHED via subject.__eq__ | subject __eq__ calls: 1
```

### E1 — bridge equality both orders — **PASS**

`concrete == proto` and `proto == concrete` are both `True` when canonical names agree, both `False`
when they differ. The canonical-name bridge works symmetrically across the two distinct types (each side's
`__eq__` reads the other's `_fltk_canonical_name`; reflected `__eq__` covers the order the subject can't).

### E2 — `match` value pattern routes through the bridge across types — **PASS**

Protocol values held as class attributes (`Proto.items`) so `case Proto.items:` is a dotted-name VALUE
pattern (not a capture). `match concrete: case Proto.items:` SUCCEEDS when canonical names agree, falls
through to `case _` when they differ. `match` value-pattern equality invokes the bridge correctly across
the two different types.

### E3 — operand order used by `match` — **PASS (subject side fires)**

`match` evaluates `subject == pattern_value`, i.e. it calls the SUBJECT's `__eq__` first. Instrumented
test: a subject whose `__eq__` reads the pattern's `_fltk_canonical_name`, matched against a pattern value
with a plain identity `__eq__`, MATCHED with exactly 1 call to the subject's `__eq__`. **Implication:** the
concrete-backend instance is the `match` subject, so the concrete-side bridge `__eq__` alone suffices —
no reliance on the protocol-value's reflected `__eq__`. (Both sides define the bridge anyway, so even the
reverse direction in E1 works, but `match` only needs the subject/concrete side.)

### E4 — Rust `kind` getter returns a bridge-equipped NodeKind — **PASS (inspect)**

`gsm2tree_rs.py` emits the Rust `NodeKind` with the SAME canonical-name bridge: each member's
`_fltk_canonical_name` getter returns `"NodeKind.<UPPER>"` (`_node_kind_block` -> `_fltk_canonical_name`,
lines 213-216; `__repr__` canonical strings, lines 204-211), and a cross-backend `__eq__`/`__hash__` that
compares via the other operand's `_fltk_canonical_name` (`_emit_rust_cross_backend_eq_hash`, lines
150-179: `other.getattr("_fltk_canonical_name")` then `self.__repr__() == cn_str`). Each node's
`#[getter] fn kind(&self) -> NodeKind` returns that enum (lines 349-358). So a Rust-produced node's
`.kind` is a `NodeKind` carrying the identical `"NodeKind.ITEMS"` canonical string and the same bridge —
`match rust_node.kind: case cst.<Node>.kind:` routes through `subject.__eq__` (the Rust bridge) exactly
as the Python case does in E2/E3.

### Cross-backend bottom line

`match child.kind: case cst.<Node>.kind:` WORKS for a protocol-only consumer against BOTH Python and Rust
instances. `match` compares `subject == pattern_value`, so the concrete-backend instance (Python enum or
Rust pyclass) is the subject, and its canonical-name bridge `__eq__` resolves equality against the
protocol module's distinct `kind` object by `_fltk_canonical_name`. Agreement of the canonical string
("NodeKind.<UPPER>") across protocol, Python backend, and Rust backend is the single invariant the whole
mechanism rests on — and all three emit it identically. No `cast`, no enum-namespace exposure, no
backend-specific code path required.
