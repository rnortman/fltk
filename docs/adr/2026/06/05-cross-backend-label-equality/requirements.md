# Cross-Backend Label Equality — Requirements

**Date:** 2026-06-05
**Mode:** draft
**Sources:** request (inline), `exploration.md` (this dir). Background: `../05-cst-type-annotations-regression/trivia-divergence-rootcause-v2.md`, `node-suffix-investigation.md`.

> Style note (for any agent editing this doc): concise, precise, unambiguous. No padding, no exploration re-summary, no design/implementation detail.

---

## Goals

Make generated CST `Label` enum members compare and hash equal across backends (Python dataclass CST and Rust/PyO3 CST) whenever they denote the same grammar label, keyed on a stable canonical name. Downstream comparisons like `node_label == fltk_cst.Items.Label.NO_WS` keep working regardless of which backend produced the label.

**Motivation (LIVE problem, not future-proofing):** FLTK has out-of-tree consumer applications that compare CST node labels against static module-level `cst.X.Label.Y` enum constants. These comparisons are correct today only because those consumers run a single backend (Python CST). The moment such a consumer adopts the Rust backend — or mixes backends (e.g. holds a label parsed with one backend and compares it against the other backend's constant) — those comparisons silently start returning `False` and the consumer breaks. This cycle prevents that breakage. The absence of an *in-tree* consumer exercising the cross-backend path is **not** evidence the feature is unneeded: the consumers that need it are out of tree, and they already depend on this equality holding. The in-tree work (including the `self.cst` removal in §AC10) is a demonstration that the contract holds for both backends, not the justification for the contract.

---

## In scope

- The `Label` enum members emitted by `gsm2tree.py` (Python CST) and `gsm2tree_rs.py` (Rust CST).
- Equality (`==` / `__eq__`), inequality (`!=`), hashing (`__hash__`), and membership (`in`) semantics of those members, across and within backends.
- The equality/hash contract as a stated property of generated label types (both generators co-emit it).

## In scope (continued) — `self.cst` removal from `fltk2gsm.py`

Removing the `self.cst` module dependency from `fltk2gsm.py` is **in scope** this cycle, as the in-tree demonstration that cross-backend label equality works for both backends. This **revises** the prior requirement (which listed `self.cst` removal and the `isinstance(item, self.cst.Item)` dispatch as out of scope). Two sub-parts:

- **Label comparisons:** every `fltk2gsm.py` label comparison (`==`, `!=`, `in`) must reference static module-level `cst.ClassName.Label.X` constants (a single fixed module, e.g. the Python CST module) instead of `self.cst.ClassName.Label.X`. Because of cross-backend label equality, these static comparisons must return correct results regardless of which backend produced the stored label being compared. This is the load-bearing demonstration.
- **`isinstance` dispatch:** the `isinstance(item, self.cst.Item)` dispatch sites (`fltk2gsm.py:69,80`) must be reworked so that `self.cst` is no longer needed anywhere in `fltk2gsm.py`. See Open question 5 — if a genuine technical obstacle prevents fully eliminating `self.cst` (e.g. the dispatch fundamentally requires backend-specific node type identity that label equality cannot supply), that obstacle is captured as an explicit open question for design rather than silently narrowing the criterion.

The end-state goal: `self.cst` is absent from `fltk2gsm.py`; the file compares against static `cst` constants and works for both backends.

## Out of scope

- Cross-backend equality of CST **node** objects (only `Label` members are covered).
- IntEnum-based value equality — explicitly rejected (cross-class int coercion footgun).
- The trivia / `capture_trivia` divergence between backends (separate concern; see background doc).
- Protocol class naming (`*Node` suffix); separate concern.
- Changing label names, label ordinals, or grammar semantics.

---

## Definitions

- **Canonical name:** the stable, backend-independent string identifying a grammar label, of the form `"<ClassName>.Label.<LABEL_NAME>"` (e.g. `"Items.Label.NO_WS"`). `<LABEL_NAME>` is the uppercased label as already used for the Python enum member name and the Rust `#[pyo3(name=...)]`. This string is already emitted by the Rust generator's `__repr__` (`gsm2tree_rs.py:170-172`; baked into `cst_generated.rs:27,244`).
- **Backend:** a module providing CST classes + `Label` enums. Note there are ≥3 distinct label-bearing module instances that must interoperate: the Python CST module, `fltk._native.fegen_cst`, and `fegen_rust_cst` (separate Rust crates → distinct Python types for the same grammar; see exploration §7.4).
- **Denote the same grammar label:** two members are equal iff their canonical names are equal. Canonical name is the **sole** equality key; it is **rule+label scoped** and does **not** encode grammar identity. Consequences:
  - Members from the same grammar with different `<ClassName>` or `<LABEL_NAME>` differ in canonical name → not equal.
  - Two **distinct rules** that legitimately share the same `<ClassName>.Label.<LABEL_NAME>` are by construction the same label key → equal (intended).
  - Two **unrelated grammars** that each define `<ClassName>.Label.<LABEL_NAME>` with identical strings produce equal members. This cross-grammar collision is possible because canonical name does not carry grammar identity. Whether to accept this is Open question 4; the definition does not claim `<ClassName>` provides grammar-level disambiguation.

---

## System behavior

Let `A` and `B` be `Label` members from any two backends (possibly the same backend).

### Equality

1. `A == B` is `True` iff `A` and `B` have the same canonical name; `False` otherwise.
2. Equality is **reflexive**: `A == A` is `True`.
3. Equality is **symmetric**: `A == B` and `B == A` yield the same boolean, for every ordering of backends (`py == rust` and `rust == py`; `fegen_cst == fegen_rust_cst` and reverse).
4. Equality is **transitive** across all backends: if `A == B` and `B == C` then `A == C`.
5. `A != B` is the logical negation of `A == B` for all cases above.

### Comparison against unrelated objects

6. Comparing a `Label` member against an object that is not a `Label` member of any backend (arbitrary object, `None`, an int, a string, an enum from an unrelated type) **never raises**. It returns `False` for `==` and `True` for `!=`. An `__eq__` MAY return `NotImplemented` here so Python falls back to reflected comparison / identity → `False`. **Caveat:** returning `NotImplemented` is acceptable *only* where the correct answer is `False` (not-a-label or different-canonical-name cases). For the equal case (§1, AC1), at least one side's `__eq__` MUST return `True` as a value — if both sides returned `NotImplemented`, Python would fall back to identity and yield a wrong `False`.
7. In particular, comparison against the canonical-name string itself (e.g. `label == "Items.Label.NO_WS"`) returns `False` — labels compare equal only to other labels, not to bare strings. (Avoids the int-coercion-style footgun in string form.)

### Hashing

8. `hash(A) == hash(B)` whenever `A == B` (hash consistent with eq). Concretely, hash is derived from the canonical name so equal members across backends hash identically.
9. `Label` members are usable as `set` elements and `dict` keys. A member from backend `A` and an equal member from backend `B` collapse to one entry: `{A, B}` has length 1; `B in {A}` is `True`.

### Membership

10. `X in (a, b, c)` and `X in [a, b, c]` and `X in {a, b, c}` return `True` iff `X` equals at least one element by the equality rules above, regardless of which backend produced `X` vs the container elements. (Covers the `fltk2gsm.py:52-56` tuple-membership pattern across backends.)

### Generated filter compatibility

11. Existing generated `children_X` filters (`label == ClassName.Label.X` in both Python and Rust CST) continue to return the same results as today for the same-backend case. Cross-backend equality must not change same-backend filter outcomes (it only *adds* equalities that were previously `False`).

---

## Acceptance criteria

Concrete, observable. Backends below: `py` = Python CST module, `rust` = a Rust CST module (`fegen_rust_cst` and/or `fltk._native.fegen_cst`).

- **AC1 (cross eq, both directions):** `py.Items.Label.NO_WS == rust.Items.Label.NO_WS` is `True` and `rust.Items.Label.NO_WS == py.Items.Label.NO_WS` is `True`.
- **AC2 (cross ineq):** `py.Items.Label.NO_WS == rust.Items.Label.WS_ALLOWED` is `False`; `!=` is `True`, both directions.
- **AC3 (same-backend unchanged):** within each backend, `X == X` is `True` and distinct members are `!=`; pre-existing same-backend tests still pass.
- **AC4 (hash consistency):** `hash(py.Items.Label.NO_WS) == hash(rust.Items.Label.NO_WS)`.
- **AC5 (set/dict collapse):** `len({py.Items.Label.NO_WS, rust.Items.Label.NO_WS}) == 1`; `rust.Items.Label.NO_WS in {py.Items.Label.NO_WS}` is `True`; a dict keyed by one retrieves with the other.
- **AC6 (membership across backends):** `rust.Items.Label.NO_WS in (py.Items.Label.NO_WS, py.Items.Label.WS_ALLOWED)` is `True`.
- **AC7 (no raise on unrelated):** each of these returns a boolean without raising: `py.Items.Label.NO_WS == None`, `== 1`, `== "Items.Label.NO_WS"`, `== object()`, `== rust.Disposition.Label.INCLUDE` (different rule). All `==` are `False`; the corresponding `!=` are `True`. Symmetric (`None == label`, etc.) likewise never raises.
- **AC8 (third module):** AC1, AC4, AC6 also hold when one side is `fltk._native.fegen_cst` and the other is `fegen_rust_cst` (distinct Rust crates).
- **AC9 (label-compare backend independence):** the *label comparisons* (`==`, `in`) inside `Cst2Gsm` (`fltk2gsm.py`) succeed whenever the stored label and the static `cst.ClassName.Label.X` constant denote the same grammar label, regardless of which backend produced each. Demonstrated by an isolated check: a label held from backend `A` compares equal (and is `in`-found) against the corresponding constant from a single fixed backend module's constant.
- **AC10 (`self.cst` eliminated from `fltk2gsm.py`):** after this cycle, `self.cst` no longer appears in `fltk2gsm.py`. All label comparisons reference static module-level `cst.ClassName.Label.X` constants (a single fixed module), and the `isinstance(item, self.cst.Item)` dispatch sites are reworked so the injected backend module is no longer needed. Concretely:
  - `fltk2gsm.py` processes a CST produced by **either** backend and yields the correct `gsm.Grammar`, with label comparisons against the static `cst` constants returning correct results in both cases (this is the in-tree demonstration that cross-backend label equality holds for both backends).
  - Existing `test_phase4_fegen_rust_backend.py` parity assertions (Python-backend and Rust-backend CST both yield equal `gsm.Grammar`) continue to hold, now without `self.cst` injection driving the dispatch.
  - **Caveat — isinstance dispatch (Open question 5):** if a genuine technical obstacle prevents fully removing `self.cst` (e.g. the `isinstance(item, self.cst.Item)` dispatch fundamentally requires backend-specific node type identity that label equality alone cannot replace), that obstacle is recorded as Open question 5 for design to resolve, **not** silently dropped from AC10. The default expectation is full removal; any retained `self.cst` usage must be justified there.

---

## User-visible surface

- **API contract:** generated `Label` members carry the stated eq/hash semantics. This is a property of generated code; both generators emit it together (co-generated; drift is a non-issue per request).
- **`fltk2gsm.py` surface change:** `self.cst` is removed (per §AC10). Any external caller constructing `Cst2Gsm` with a `cst=` argument is affected — design must decide whether the constructor parameter is dropped, ignored, or retained as a no-op. Flagged for design under Open question 5; behavior of the transformation (correct `gsm.Grammar` for both backends) is unchanged.
- **`repr` / canonical name:** the canonical-name string `"<ClassName>.Label.<LABEL_NAME>"` is the equality key. Rust already exposes it via `__repr__`. Requirement: the same canonical string is available consistently on both backends as the equality basis. Whether it is additionally surfaced as a named property (e.g. `.canonical_name`) is an open question (see below); not required by the goal unless a consumer needs programmatic access.
  - Python `repr` today is `"<Label.NO_WS: N>"` / `str` is `"Label.NO_WS"` (no class prefix). Requirement does **not** mandate changing Python `repr`/`str`, only the eq/hash behavior. If matching `repr` across backends is desired, that is an open question.
- **No new config, CLI flags, env vars, or error messages.**
- **Errors/logs:** none added. Comparison must not emit warnings or logs.

---

## Constraints

- **Compatibility:** existing external downstream comparisons (`node_label == fltk_cst.Items.Label.NO_WS`, membership tests in `bootstrap2gsm.py`, test sites) must keep working with unchanged source; cross-backend behavior is purely additive for them. **Exception:** `fltk2gsm.py` itself is edited this cycle (per §AC10) to drop `self.cst` and compare against static `cst` constants — that is intended in-scope work, not a compatibility break, and its observable behavior (correct `gsm.Grammar` for both backends) is preserved.
- **`__hash__` / `__eq__` invariant:** must remain mutually consistent (Python data model requirement; labels are used in membership tests and sets/dicts).
- **Symmetry & non-raising:** as specified in System behavior §3, §6 — required because Python evaluates both `a == b` and reflected `b == a`. **Both** generators must emit custom equality, not just one: the Python `Label` (a plain `enum.Enum`) has identity-based `__eq__` that will never delegate to a canonical name, so the Python side needs its own `__eq__`/`__hash__` override; and the Rust `#[pyclass(eq, hash, frozen)]` derive handles only same-type comparison and must be replaced/supplemented with a custom richcmp + hash tolerating foreign operands. For the `py == rust` direction to reach `True`, the Python side's `__eq__` must yield `NotImplemented` (not `False`) for a foreign operand so Python invokes the reflected Rust richcmp; a Rust-only fix is insufficient. (Behavior is already pinned by AC1/AC7; this note prevents a one-sided implementation.)
- **Frozen / immutable:** label members remain immutable singletons within a backend (no change to that property).
- **No IntEnum:** value-based int equality is prohibited.
- **Co-generation:** the contract is emitted by `gsm2tree.py` and `gsm2tree_rs.py` together. No runtime cross-backend registry or shared mutable state is required by these requirements; equality is computed from the canonical name each side already knows.
- **Performance (non-blocking SHOULD; mechanism is design's call):** equality/hash sit on hot paths (`children_X` filters run per child during CST traversal). The design SHOULD avoid introducing per-comparison Python-object allocation or string formatting on the same-backend path, and cross-backend comparison SHOULD be O(length of canonical name) at worst. There is no measured perf acceptance criterion; "no meaningful same-backend regression" is a design goal, not a gated AC. The *technique* (precompute, intern, static `&'static str` match as Rust `__repr__` already does, integer keying, etc.) is left to design per the request's "mechanism is design's call." If a measurable regression is observed in practice, treat it as a design defect to revisit, not a requirements change.

---

## Open questions

1. **canonical_name property exposure.** Should the canonical name be a public named attribute (e.g. `label.canonical_name`) on both backends, or remain internal to the eq/hash implementation (with `repr` as the only string view)?
   - *Option A (internal only):* satisfies the goal; minimal surface. **Proposed default.**
   - *Option B (public property):* enables consumers to key on the string directly; larger committed API surface.
   - Redirect: user says "expose `.canonical_name`" → choose B.

2. **Python `repr`/`str` alignment.** Should Python's `repr`/`str` change to emit `"Items.Label.NO_WS"` (matching Rust's `__repr__`), for cross-backend debugging symmetry?
   - *Option A:* leave Python `enum` default repr (`"<Label.NO_WS: N>"`) unchanged. **Proposed default** (out of stated goal; eq/hash is the contract).
   - *Option B:* align repr across backends.
   - Redirect: user says "make reprs match" → B.

3. **String equality (AC7 line on `== "Items.Label.NO_WS"`).** Spec currently says comparison to a bare canonical-name **string** returns `False` (labels equal only labels). Confirm this is desired vs. allowing string convenience comparison.
   - *Proposed default:* `False` (string compare rejected — symmetry/footgun concerns mirror the IntEnum rejection).
   - Redirect: user says "allow string comparison" → AC7 and §7 change to make `label == "Items.Label.NO_WS"` `True` (and define reflected `str == label` symmetry + hash implications).

4. **Distinct-grammar collision semantics.** Two unrelated grammars could each define `Items.Label.NO_WS`; their canonical names would be identical and thus compare equal. Is canonical name intended to be grammar-scoped (unique per grammar) or is collision across grammars acceptable / impossible in practice?
   - *Proposed default:* accept that canonical name is rule+label scoped only; cross-grammar collision is out of scope (a single process rarely mixes two grammars' CSTs, and where it does the labels genuinely denote "the same label name" by the canonical-name definition). 
   - Redirect: user says "must disambiguate by grammar" → canonical name gains a grammar identifier component; AC definitions update.

5. **`isinstance` dispatch removal from `fltk2gsm.py` (TODO: isinstance-dispatch-removal).** AC10 requires `self.cst` to be fully removed from `fltk2gsm.py`, including the `isinstance(item, self.cst.Item)` dispatch sites (`fltk2gsm.py:69,80`). Per exploration §182-195, `isinstance` against a PyO3 native class tests native type identity and cannot be satisfied by label equality alone — so the dispatch must be reworked by a different mechanism (e.g. dispatch on the label value itself rather than on node type, or against a static-module class that both backends' nodes satisfy). Design must determine the mechanism.
   - *Proposed default:* rework dispatch to key on the (now backend-independent) label rather than `isinstance` node-type checks, so `self.cst` is fully eliminated and the static-`cst` comparison is the sole driver.
   - *Genuine-obstacle escape:* if design finds the `isinstance` checks carry semantic information label equality cannot reconstruct (i.e. two grammar constructs share a label but need distinct node-type handling), record the specific obstacle and the minimal retained `self.cst` usage here; AC10 then narrows to "static `cst` label comparisons + minimal documented `isinstance` residue" rather than full removal. This escape is for a *demonstrated* technical obstacle only — not for convenience or scope-trimming.
   - Redirect: user says "full removal is mandatory, find a way" → escape is closed; design must eliminate all `self.cst` usage.

---

**Verdict:** READY-FOR-REVIEW
