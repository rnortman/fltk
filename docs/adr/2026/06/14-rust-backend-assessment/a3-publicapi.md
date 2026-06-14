# A3 — Public-API / Downstream-Consumer Compatibility (the CLAUDE.md crown jewel)

Dimension: Is the generated Rust CST a genuine NEAR-DROP-IN for the Python CST from an
OUT-OF-TREE consumer's perspective? Concretely: renamed public symbols, changed accessor
signatures, type-annotation churn, equality/ordering/repr differences, import-path churn,
.pyi correctness. Does "downstream updates imports but not annotations/call sites" actually
hold?

Method: I did not rely on the understanding notes alone — I **built the fegen Rust fixture
and ran both backends side by side**, comparing real objects. Every divergence below is
reproduced with a concrete command and observed output, not inferred from reading the
generator.

## Verdict

**Adequate, with documented sharp edges.** The hard CLAUDE.md red lines are NOT crossed:
node class names are byte-identical (no `Node` suffix), the label/NodeKind namespaces match,
accessor *names* match, cross-backend enum equality genuinely works, and the in-tree consumer
(`fltk2gsm.py`) runs on **both backends with its CST type annotations fully intact** against a
single shared protocol module. That is the crown-jewel result and it holds.

But "drop-in" is the wrong word; "near-drop-in with fine print" is honest. There are **four
runtime divergences where correct-looking, protocol-conforming consumer code works on one
backend and silently misbehaves or raises on the other** — all type-undetectable because the
protocol's annotations describe Python's behavior and the Rust runtime differs. The worst is
`node.children` in-place mutation: a silent no-op on Rust, a real tree edit on Python, and the
protocol types `children` as a mutable `list`, actively inviting it. There is also one real,
already-shipped annotation-surface change (the `span` union widening) that forces a `cast` at
uncast call sites, and a transient-but-real annotation-strip regression in history (214dbe1)
that was later repaired.

None of these force *wholesale* annotation churn. They are bounded. But each is a concrete
production trap for an out-of-tree consumer switching Python→Rust, and they are guarded only by
documentation + parity tests, not by the type system.

---

## What HOLDS (the drop-in story is real here)

### Node class names: identical, no `Node` suffix
`dir()` of both fegen backends yields the same node classes: `Alternatives, BlockComment,
Disposition, Grammar, Identifier, Item, Items, LineComment, Literal, NodeKind, Quantifier,
RawString, Rule, Term, Trivia`. `cst.Item.__name__ == rc.Item.__name__ == "Item"`. The Rust
generator delegates naming to the shared `naming.snake_to_upper_camel` via `self._py_gen`
(gsm2tree_rs.py:180) and pins the Python-visible name with `#[pyclass(name = "{class_name}")]`
(gsm2tree_rs.py:1166). **The crown-jewel red line (renamed public symbols) is not crossed for
node classes.**

### Cross-backend enum equality genuinely works
Verified live: `py.NodeKind.ITEM == rc.NodeKind.ITEM` → `True`, hashes agree, and
`py.Item.Label.TERM == rc.Item.Label.TERM` → `True`. `cst.Item().kind == rc.NodeKind.ITEM` →
`True`. This is the canonical-name scheme (`_fltk_canonical_name` string compare) emitted in
all three places. It is the load-bearing thing that makes `match node.kind: case
cst.Item.kind` dispatch identically over either backend's tree, and it actually works.

### The in-tree consumer keeps its annotations on both backends (the key positive)
`fltk/fegen/fltk2gsm.py` imports `from fltk.fegen import fltk_cst_protocol as cst` and its
visit methods are fully CST-typed: `visit_grammar(self, grammar: cst.Grammar)`,
`visit_item(self, item: cst.Item)`, etc. (fltk2gsm.py:14,108…), and it uses module-level
`cst.Items.Label.NO_WS`. The **same annotated code runs on the Python dataclass backend and the
Rust PyO3 backend** — the single protocol module is the contract both satisfy. `Cst2Gsm.__init__`
takes only `terminals` (no `cst=` injection). This is exactly the CLAUDE.md goal achieved: a
real consumer switches backends with zero annotation or call-site edits.

### Hashability, `__module__`, isinstance, bool — consistent (NOT findings, ruled out)
- Both backends' nodes are **unhashable** (`TypeError: unhashable type`). Python dataclass with
  default `eq=True` sets `__hash__=None`; Rust `__hash__` raises (gsm2tree_rs.py:2161-2167). Match.
- Both report `__module__ == "builtins"` (Python exec'd module has no real name; PyO3 default).
  Match — not a divergence.
- Neither pickles. Consistently broken, so not a *divergence*.
- `isinstance(node, Cls)` and `bool(node)` behave identically within a backend.

### Error-message text is parity-matched
Even the *Python* backend emits `"Item.insert: label argument is not a Item_Label; got str"`
(using the Rust-style flat `Item_Label` name) so the two backends produce byte-equal mutator
error strings. Verified live on both.

---

## What DIVERGES (the findings)

### F1 (MAJOR) — `node.children` in-place mutation: real edit on Python, silent no-op on Rust
The single highest-severity trap. Reproduced:
```
Python children after in-place append: 2   # node.children.append(...) edits the tree
Rust   children after in-place append: 1   # silent no-op — snapshot discarded
```
The Rust `children` getter rebuilds a fresh `PyList` snapshot every call
(gsm2tree_rs.py:1304-1338, esp. comment :1307-1311). Python returns the node's **live**
`list`. The protocol types `children: list[tuple[Label|None, ...]]` (e.g.
fltk_cst_protocol.py:109) — a *mutable* `list`, not a read-only view — so a consumer is
type-clean writing `node.children.append(...)` or `node.children[i] = ...`. On Python it works;
on Rust the write vanishes with no error. **Type-undetectable, silent, data-correctness bug for
any consumer that mutates `children` in place.** The sanctioned path
(`insert/remove_at/replace_at/clear`) is identical on both backends, but the protocol's typing
does not steer consumers toward it.

### F2 (MAJOR) — `children_<label>()` returns Iterator on Python, list on Rust — mutually crashing
The protocol declares `children_<label>(self) -> typing.Iterator[T]` (e.g.
fltk_cst_protocol.py:131). Reproduced:
```
Python children_name() type: generator   Rust children_name() type: list
Python next(...) -> works                 Rust next(...) -> TypeError: 'list' object is not an iterator
Python len(...) -> TypeError              Rust len(...) -> works (returns 1)
```
A consumer who follows the **protocol's own annotation** and writes
`next(node.children_name())` is type-clean and works on Python but **raises `TypeError` on
Rust**. Conversely `len(...)` works on Rust but raises on Python. The stub even admits the lie
(gsm2tree_rs.py:381-384 "stub/runtime diverge"). The protocol annotation is correct for exactly
one backend; whichever a consumer programs against, the other can crash. This is a genuine
cross-backend behavioral incompatibility on a method the protocol exposes.

### F3 (MAJOR) — `__repr__` text differs structurally between backends
Reproduced:
```
Python: Identifier(kind=<NodeKind.IDENTIFIER: 9>, span=Span(start=-1, end=-1), children=[])
Rust:   Identifier(span=Span(start=-1, end=-1), children=[<0 child(ren)>])
```
Python uses the dataclass-generated repr: includes `kind`, includes the **full recursive
children content**. Rust (gsm2tree_rs.py:2169-2180) omits `kind`, and **summarizes** children
as `[<N child(ren)>]` rather than showing them. Consequences for an out-of-tree consumer:
- Any code that snapshots/asserts on `repr(node)` (golden-file tests, debug logs, error
  reports, `__repr__`-based serialization) produces different output and breaks on switch.
- Rust's repr is *lossy* — a debugging session that relies on `repr` to see the tree gets a
  child count on Rust but the actual children on Python.
`repr` is not in the protocol contract, so this is "out-of-contract," but `repr` is de-facto
public API that real debugging/logging/test code depends on. Not type-detectable.

### F4 (MAJOR) — span hand-in asymmetry: Rust mutators reject `terminalsrc.Span`
Reproduced:
```
Python append_name(native Span): OK
Rust   append_name(terminalsrc.Span): TypeError: Identifier: unsupported child type Span
```
Python mutators accept both `terminalsrc.Span` and `fltk._native.Span`; Rust accepts only the
native span. The protocol's mutator child type uses the backend-selecting alias
`fltk.fegen.pyrt.span.Span`, which is type-clean, but at runtime a consumer that constructs
`terminalsrc.Span(...)` objects (the natural thing on the Python backend) and hands them to a
node **hits a runtime `TypeError` after switching to Rust**. Call-site change forced for such
consumers (construct native spans instead). Deliberately excluded from the exact-parity matrix
(per u4), i.e. known and unfixed.

### F5 (MAJOR) — positional pattern matching breaks on Rust (`__match_args__` absent)
Reproduced:
```
Python __match_args__: ('kind', 'span', 'children')   Rust __match_args__: ABSENT
Python:  case cst.Identifier(k, s, c)  -> matches
Rust:    case rc.Identifier(k, s, c)   -> TypeError: Identifier() accepts 0 positional sub-patterns (3 given)
```
Python dataclasses auto-generate `__match_args__`, enabling **positional** structural pattern
matching. The Rust pyclass has none. A consumer writing `case Item(kind, span, children):`
(positional) is type-clean (pyright accepts it against the dataclass-shaped protocol) and works
on Python but **raises `TypeError` on Rust**. Keyword/class patterns (`case Item(kind=k):`)
work on both — verified — so this only bites positional captures, but `match` is a primary CST
traversal idiom and positional capture is idiomatic. Type-undetectable.

### F6 (MINOR) — `span` union widening forces a `cast` at uncast call sites (shipped annotation churn)
The protocol `span` annotation is the union `terminalsrc.Span | fltk._native.Span`
(fltk_cst_protocol.py:108, widened in commit 4c8f0ad to accommodate the native Rust Span).
Verified with pyright:
```
error: Argument of type "terminalsrc.Span | fltk._native.Span" cannot be assigned to
       parameter "s" of type "Span" ... "fltk._native.Span" is not assignable to
       "fltk.fegen.pyrt.terminalsrc.Span" (reportArgumentType)
```
A consumer that previously passed `node.span` (uncast) into a `terminalsrc.Span`-typed function
was type-clean; after the widening it must add a `typing.cast` or widen its own signature. The
team documents this honestly in-tree (fltk/fegen/test_cst_protocol.py:592-614: "uncast call
sites DO require annotation changes after widening… the compatibility claim applies to code
that uses typing.cast"). It is additive and bounded, but it IS exactly the type-annotation-
surface change CLAUDE.md flags, and it lands on **every** consumer the moment the Rust backend
becomes an option — even one who never switches — because it is a change to the shared protocol.

### F7 (MINOR) — extra module-level `<Class>_Label` symbols on the Rust backend only
Reproduced: the Rust `cst` module exposes `Item_Label, Grammar_Label, …` as module-level
symbols; the Python backend exposes only the nested `Item.Label`. `Item.Label.__qualname__` is
`"Item.Label"` on Python but `"Item_Label"` on Rust. Consequences:
- `from cst import *` imports a different symbol set across backends.
- Consumer code that introspects `label.__class__.__qualname__` (e.g. for diagnostics) sees
  `Item.Label` vs `Item_Label`.
The protocol advertises only the nested `Cls.Label` form (which is reachable on both via the
`#[classattr] Label` shim, gsm2tree_rs.py:1293-1302), so this is out-of-contract, but it is a
genuine asymmetry in the public module namespace, and the differing `__qualname__` is
observable by conforming consumers.

### F8 (NIT / HISTORICAL) — the 214dbe1 annotation-strip regression (resolved)
For the record: commit 214dbe1 (Phase 4) **stripped every CST type annotation** off
`fltk2gsm.py`'s visit methods (`grammar: cst.Grammar` → `grammar`) and switched labels to
injected `self.cst.Items.Label.X`, purely to make one code path run on both backends. That was
a textbook CLAUDE.md violation (forced annotation churn on the in-tree consumer). It was
**later repaired** by the clean-protocol-consumer-api work (annotations restored against the
shared protocol module — see "What HOLDS"). Reported not as a live finding but as evidence that
the drop-in invariant is fragile and was actually broken mid-project before being recovered;
the recovery cost a whole new generated artifact (the 936-line protocol module + tri-located
canonical-name eq/hash).

---

## Cross-backend NODE equality is False (context, not itself a finding)
`cst.Identifier() == rc.Identifier()` → `False` (both directions). The carefully-built
cross-backend equality contract covers **enums (Label/NodeKind) only**, not node objects: the
Rust node `__eq__` returns `NotImplemented` for any non-Rust-handle operand
(gsm2tree_rs.py:2148-2151), and the Python dataclass `__eq__` only matches same-type. This is
**not a real consumer trap** because a deployment runs exactly one backend at a time — within a
backend, node `==` is consistent and correct (both compare span + children; verified). I flag it
only to bound the equality claim: the equivalence machinery does NOT make a Python node equal a
Rust node, and any test harness that compares trees across backends must use the structural
`parser_parity.assert_cst_equal` helper, not `==`.

---

## Bottom line for the dimension
The non-negotiable red lines (renamed public symbols; wholesale annotation rewrites) are **not**
crossed: node names match, enum equality works, and the in-tree consumer keeps full annotations
on both backends against a single protocol contract — the design is the right shape. But the
"drop-in" label oversells it. There are four type-undetectable runtime divergences (F1 children
in-place no-op, F2 Iterator-vs-list, F3 repr, F4 span hand-in) and one positional-`match` break
(F5) where conforming consumer code works on Python and misbehaves/raises on Rust, plus one
shipped annotation-surface change (F6 span widening). The protocol's `list[...]` and
`Iterator[T]` annotations actively describe Python semantics that the Rust runtime does not
honor, so the type checker cannot catch the worst trap (F1). All are guarded by docs + parity
tests, not by construction — consistent with the project-wide "two string generators kept in
lockstep by tests" liability. Honest label: **near-drop-in, sound for read/dispatch, sharp on
mutation and on protocol-implied iteration/positional-match semantics.**
