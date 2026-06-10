# Forensic Report: How Rust CST Nodes Ended Up With `span: PyObject`

Concise. Precise. Token-dense. No fluff, no padding. Audience: smart human/LLM.

---

## 1. Timeline

### Pre-planning: Exploration and synthesis (2026-05-25)

`docs/adr/2026/05/25-rust-backend-exploration/` is a multi-document exploration of Rust
backend options. The synthesis (`synthesis.md`) covers all four paths (IIR backend, per-lang
generators, hybrid, full Rust). Under "Path 1" it identifies PyO3 CST interface fidelity as
a cross-cutting risk:

> "Heterogeneous `children` list: `list[tuple[Label|None, Union[...]]]` with direct
> indexing, slicing, striding (`children[::2]`), `len()`, `isinstance()` on elements. Must
> present as a real Python list of real Python tuples."
— `synthesis.md:72-73`

The feasibility analysis `analysis-rust-cst-first.md` specifically studies "Rust+PyO3 CST
Nodes as Intermediate Step." It names the approach explicitly as an **intermediate step**
and a **stepping stone**:

> "As a stepping stone to Rust parser/unparser... When the parser is also Rust, `children`
> can switch from `Py<PyList>` to `Vec<(Label, CstChild)>` -- a Rust-native representation."
— `analysis-rust-cst-first.md:225-229`

The analysis also contains the first recorded selection of `PyObject` for span:

> "Per-node `#[pyclass]` struct | ~15 per node | `span: PyObject`, `children: Py<PyList>`"
— `analysis-rust-cst-first.md:250`

The explicit rationale for `Py<PyList>` children was that Option A (Vec with conversion)
breaks mutation semantics used by 11 call sites in `fltk_parser.py`, and Option C (custom
`__getitem__`) requires reimplementing full Python list slicing semantics. Option B was
selected:

> "Option B is the only one that preserves semantics without reimplementing the Python list
> protocol. The performance cost is real but acceptable for an intermediate step."
— `analysis-rust-cst-first.md:97`

The feasibility analysis explicitly acknowledged the "nominal" quality of the Rust backing:

> "With Option B (children as `Py<PyList>`), the Rust struct is essentially a thin wrapper
> around Python objects. The 'Rust backing' is nominal."
— `analysis-rust-cst-first.md:223`

The analysis also acknowledged that `Py<PyList>` children would be **throwaway work** when
a Rust parser arrives:

> "If the final goal is a Rust-native `children` representation, the Option B approach
> (children as `Py<PyList>`) is throwaway work for the `children` field."
— `analysis-rust-cst-first.md:234`

**No rationale for `span: PyObject` specifically appears in the feasibility analysis** beyond
the table entry quoted above. The analysis does explain the span's dual role (node field +
leaf terminal value, `analysis-rust-cst-first.md:139-148`) and states a PyO3 `#[pyclass(frozen)]`
Span satisfies both roles — but that design was for a Rust-native Span, which is what Phase 1
delivered.

---

### Phase plan decision (2026-05-25)

`docs/adr/2026/05/25-pyo3-cst-plan/phase-plan.md` is the authoritative multi-phase plan.

**Stated goal** — the plan's opening context paragraph:

> "The Rust backend ADR (`25-rust-backend-exploration/`) chose PyO3-wrapped Rust CST nodes as
> the first deliverable."
— `phase-plan.md:8`

> "**Primary deliverable:** `plumbing.generate_parser()` produces Rust-backed CST nodes for
> ANY user grammar."
— `phase-plan.md:12`

The plan does NOT state "performance" as the primary goal for Phase 4; it frames Phases 1-4
as producing selectable Rust CST nodes. The performance question is explicitly unresolved:

> "**Risk R5:** Rust CST nodes with `Py<PyList>` children may be *slower* than Python
> dataclasses due to FFI overhead on every method call. No baseline profiling data exists...
> Accept that this intermediate step trades performance for infrastructure establishment."
— `phase-plan.md:243-245`

The plan's Phase 5 ("Dogfooding") described replacing `fltk_cst.py` with Rust. There is no
Phase 6 in the plan for a Rust parser or native Rust spans on the parse path. The plan stops
at Phase 5.

---

### Phase 1: Rust Span exists but is NOT used on the parse path (commit `0f9b786`)

Phase 1 built a Rust `Span` class with `Arc<SourceInner>` for source-bearing capability.
The design explicitly stated:

> "**Phase 1 scope note:** Phase 1 delivers the *capability* for source-bearing spans and
> validates it via synthetic construction (`Span.with_source`). No production parse path emits
> source-bearing spans in this phase. Wiring the parser to attach source text is a follow-up
> phase."
— `docs/adr/2026/05/25-pyo3-phase1-span/design.md:183`

Phase 1 also explicitly noted that the Rust Span does NOT expose `.start`/`.end`:

> "**Rust backend: `start`/`end` are private.** No `#[pyo3(get)]` — Python code cannot read
> `span.start` or `span.end` on a Rust-backed Span."
— `phase1-span/design.md:241`

This is the direct precondition for `span: PyObject` in Phase 2: the Rust `Span` type,
by design, hides `.start`/`.end` — but the Python parser, `fltk2gsm.py`, and others access
`span.start` / `span.end` on spans stored in CST nodes. A Rust-typed `span: Span` field in
a CST node would mean span access from Python breaks (`AttributeError: 'Span' object has no
attribute 'start'`).

---

### Phase 2: `span: PyObject` first introduced (commit `f7766de`)

The hand-written PoC in `src/cst_poc.rs` (replaced in Phase 3) introduced `span: PyObject`
explicitly, with documented rationale:

> "**`span` as `PyObject`**: The node accepts any Python object as a span. The Phase 2 PoC is
> standalone; the parser uses Python `Span` (from `terminalsrc`), not Rust `Span` (which lacks
> `.start`/`.end` attributes). Storing as `PyObject` avoids coupling to either Span type."
— `docs/adr/2026/05/27-phase2-nested-enum-poc/design.md:97`

Commit hash: `f7766de`. The struct definition introduced:

```rust
#[pyclass]
pub struct Identifier {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}
```
— `src/cst_poc.rs` (now deleted; pattern preserved in `src/cst_generated.rs`)

The rationale is explicit: the Rust Span's `.start`/`.end` privacy is what forces `PyObject`.
The parser always produces Python `terminalsrc.Span` objects, never Rust `Span` objects.
Storing `span` as `PyObject` lets the node hold whichever span type the parser hands it.

---

### Phase 3: Generator codifies `span: PyObject` (commit `f8a2fe1`)

`gsm2tree_rs.py` (the code generator) was written with `span: PyObject` as the fixed
template for every generated node struct. From the Phase 3 design:

> "Node Struct: Identical for every node. `span` has `get, set`; `children` has `get` only."
— `docs/adr/2026/05/27-phase3-generator/design.md:171-182`

The design document for the generator (`gsm2tree_rs.py:194`) emits:

```rust
#[pyclass]
pub struct {ClassName} {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}
```

No design document at Phase 3 questions this choice or flags it for future change.

Phase 3 also notes (in the Phase 4 design, discussing crate coupling):

> "The generated node struct stores `span: PyObject` (`gsm2tree_rs.py:194`) and
> `children: Py<PyList>` (`:196`) — both Python objects, not Rust-typed `Span`. Every span
> operation (`__eq__`, `__repr__`) goes through `self.span.bind(py).eq(...)` / `.repr()`
> — duck-typed Python dispatch. **A user extension never links the Rust `Span` type.**"
— `docs/adr/2026/05/28-pyo3-phase4-runtime-integration/design.md:60-65`

The Phase 4 design treats `span: PyObject` not as a flaw but as a feature: it means user
extensions can be standalone CDYLIBs that do not link `fltk._native` at Rust link-time.

---

### Phase 4: Selectable backends shipped (commit `214dbe1`)

Phase 4 wired `plumbing.generate_parser` to accept a `rust_cst_module` selector. The
Python parser (`fltk_parser.py`) was not changed — it still constructs nodes via
`fltk.fegen.fltk_cst.*` references, producing Python `terminalsrc.Span` objects that are
stored in Rust node `span: PyObject` fields. This is consistent with the design.

---

## 2. Was `span: PyObject` a deliberate documented decision?

**Yes, explicitly documented**, with rationale, in the Phase 2 design:

> "The parser uses Python `Span` (from `terminalsrc`), not Rust `Span` (which lacks
> `.start`/`.end` attributes). Storing as `PyObject` avoids coupling to either Span type."
— `docs/adr/2026/05/27-phase2-nested-enum-poc/design.md:97`

The decision chain:
1. Phase 1 deliberately made Rust `Span.start`/`.end` private (`phase1-span/design.md:241`).
2. The Python parser uses `span.start`/`span.end` at ~40 call sites in `fltk_parser.py` and
   throughout `fltk2gsm.py:24,126,130`.
3. Therefore, if a Rust CST node stored `span: Span` (Rust type), consumer code would break.
4. Therefore `span: PyObject` — the node stores whatever Python span object the parser
   gives it, without Rust type constraints.

The Phase 1 design also explicitly acknowledged the migration work required:

> "When (in a future phase) the Rust backend produces spans, these sites must migrate to
> `span.text()` or `span.text_or_raise()`. That migration is out of scope for Phase 1."
— `phase1-span/design.md:252`

---

## 3. Stated goal vs. what was built

### Stated goal (from earliest planning docs)

`analysis-rust-cst-first.md:9` (Section title): "Feasibility: Rust+PyO3 CST Nodes as
Intermediate Step."

`phase-plan.md:8`:
> "PyO3-wrapped Rust CST nodes as the **first deliverable**."

The synthesis (`synthesis.md:76`) frames it as:
> "**Delivery path:** Parser CST nodes first (simplest, most visible speedup), then parser
> runtime + generated parser, then unparser runtime + generated unparser."

The phase plan does NOT include a Rust parser phase in its 5-phase sequence. Phase 5 is
"Dogfooding — `fltk_cst.py` Replacement." There is no Phase 6.

The synthesis's "Missing from all analyses: Performance characterization" section is explicit
that performance goals were never quantified:

> "No analysis quantifies the current Python performance bottleneck or estimates the speedup."
— `synthesis.md:213`

### What was built

Phases 0-4: Rust CST node classes, with `span: PyObject` and `children: Py<PyList>`, selectable
via `plumbing.generate_parser(rust_cst_module=...)`. The Python parser is always used.
`terminalsrc.Span` objects (Python) flow into `span: PyObject` fields. The `Py<PyList>` children
are pure Python.

The feasibility analysis characterized this as:
> "With Option B (children as `Py<PyList>`), the Rust struct is essentially a thin wrapper
> around Python objects. The 'Rust backing' is nominal."
— `analysis-rust-cst-first.md:223`

---

## 4. Acknowledgment of gap / future-work notes

The gap (parser stays Python, spans are Python, Rust CST is nominal) is acknowledged in multiple places:

**Phase plan `phase-plan.md:225-230`** (stepping stone description):
> "When the parser is also Rust, `children` can switch from `Py<PyList>` to
> `Vec<(Label, CstChild)>`... The `Py<PyList>` approach should work but needs validation."
> "If the final goal is a Rust-native `children` representation, the Option B approach
> (children as `Py<PyList>`) is throwaway work for the `children` field."

**Phase 4 design (`28-pyo3-phase4-runtime-integration/design.md:359`)**:
> "The `Span` objects the parser writes are `fltk._native.Span` instances, stored opaquely.
> No version-pinning in Phase 4 (`TODO(rust-cst-abi-pinning)`)."

Note: This statement is factually incorrect as a characterization of the current state — the
parser always produces Python `terminalsrc.Span` objects, not `fltk._native.Span` instances.
The Phase 1 design explicitly confirmed the parse path remains on Python spans until a future
phase wires it otherwise (`phase1-span/design.md:183`).

**Phase 1 design (`phase1-span/design.md:252`)**:
> "When (in a future phase) the Rust backend produces spans, these sites must migrate to
> `span.text()` or `span.text_or_raise()`. That migration is out of scope for Phase 1."

**`TODO.md` entry `backend-with-source-signature`**:
> "Deferring until the parse path is wired to produce source-bearing spans (Phase 2+)."

This TODO uses "Phase 2+" to mean a future phase of span work, not the existing Phase 2
(PoC). It acknowledges that the parse path has never been wired to produce source-bearing spans.

---

## 5. Summary timeline

| Date | Commit | Artifact | Key decision re: spans/PyObject |
|---|---|---|---|
| 2026-05-25 | (planning) | `analysis-rust-cst-first.md` | Identifies `Py<PyList>` children as "intermediate step"; table entry shows `span: PyObject` without separate rationale |
| 2026-05-25 | (planning) | `phase-plan.md` | 5-phase plan; "parser stays Python, only node classes Rust" is the design; no Rust parser phase |
| 2026-05-25 | `0f9b786` | Phase 1 | Rust Span built; `.start`/`.end` deliberately hidden; parse path explicitly deferred |
| 2026-05-27 | `f7766de` | Phase 2 | `span: PyObject` first implemented in code; rationale explicitly documented: Rust Span hides `.start`/`.end`, Python parser uses them |
| 2026-05-27 | `f8a2fe1` | Phase 3 | Generator (`gsm2tree_rs.py`) codifies `span: PyObject` as the fixed template for all generated nodes |
| 2026-05-28 | `214dbe1` | Phase 4 | Selectable backends shipped; `span: PyObject` propagates to `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs` |

---

## 6. Open factual questions

None. The decision chain is fully documented:

1. Rust `Span` hides `.start`/`.end` by design (Phase 1).
2. Python parser and consumers use `.start`/`.end` at dozens of call sites (Phase 1 design explicitly lists them).
3. Therefore `span: PyObject` was chosen so nodes can hold Python `terminalsrc.Span` objects without type errors (Phase 2 design, explicit rationale).
4. Generator codified this (Phase 3).
5. Future migration was acknowledged but never scoped into any committed phase (Phase 1 design, `TODO.md`).
