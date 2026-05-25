# Rust Backend Exploration: Synthesis

Decision-support document. All claims anchored to source code via the three analysis reports and five exploration reports. No recommendations -- tradeoffs presented for human judgment.

---

## 1. Where the Analyses Agree

All three analyses converge on these points:

**The IIR requires zero model changes for Rust.** Every IIR node used by `gsm2parser.py` (31 symbols) and `gsm2unparser.py` (34 symbols) has a viable Rust interpretation without changing `model.py` (779 lines) or `typemodel.py` (123 lines). The Python-specific surface (walrus operator, `"and"`/`"or"` keyword strings, `isinstance`, `len(x)==0`) is confined to `py/compiler.py` (344 lines) -- the only consumer that emits language-specific code. A Rust compiler dispatches on the same IIR node subclasses and emits different syntax.

**`RefType` becomes meaningful for free.** `model.py:234-239` defines `BORROW`, `MUT_BORROW`, `OWNING`, `SHARED`, `VALUE`, `SELF`. The generators already annotate correctly (params use `BORROW`, locals use `VALUE`). The Python compiler ignores this entirely -- no `ref_type` branch in `py/compiler.py`. A Rust compiler would activate this information without changing any generator code.

**`gsm2tree.py` is the primary structural gap.** All three analyses flag this identically: `gsm2tree.py` (303 lines) bypasses IIR entirely, building Python `ast` nodes directly via `pygen`. It uses `iir.Type.make()` only for type registry keys (gsm2tree.py:69-78). CST node classes cannot be generated for Rust through the IIR pipeline without either forking `gsm2tree` or refactoring it onto IIR.

**The Rust runtime is the largest single piece of new work regardless of path.** Parser runtime (`terminalsrc.py` 68 + `memo.py` 257 + `errors.py` 71 = 396 lines Python) and unparser runtime (`combinators.py` 253 + `accumulator.py` 126 + `renderer.py` 191 + `resolve_specs.py` 539 + `pyrt.py` 35 = 1,144 lines Python) totaling 1,540 lines must be reimplemented in Rust (~2,100-2,900 lines) in every path. This is not optional and not reducible by any IR choice.

**Packrat memoization with left-recursion seed-growing is the hardest runtime piece.** `memo.py:82-156` implements the Warth/Douglass/Millstein algorithm in ~80 lines of dense state-machine logic. All analyses highlight this. Correctness testing is essential.

**The `op="is"` usage is real and needs Rust-specific handling.** Confirmed at `gsm2unparser.py:977`: `BinOp(lhs=child_label, op="is", rhs=LiteralNull())` for Python identity comparison (`x is None`). Rust equivalent: pattern matching or `x.is_none()`. A Rust compiler must special-case this -- `"is"` is not a valid Rust operator.

---

## 2. Where the Analyses Disagree or Create Tension

### IIR adaptation vs. alternative IRs

**Analysis 1 (IIR Adaptation)** concludes the IIR is already suitable as-is, needing only ~500 lines of new Rust compiler + ~150 lines type registry. Total new Python: ~650 lines. Reuses 2,305 lines of generator code unchanged.

**Analysis 2 (Alternative IRs)** raises the possibility that the IIR is "heavily Python-flavored" and considers whether a redesigned language-neutral IR would be better. It lists 13 Python-specific aspects. However, its own Section 4.2 confirms that most of these are compiler-output concerns, not model deficiencies -- the same nodes can be compiled differently.

**Resolution:** The tension is largely resolved by Analysis 1's node-by-node audit. The Python specificity lives in the compiler's output strings, not in the IIR model's semantics. `LetExpr` (the most Python-specific node) is always used inside `If`/`WhileLoop` conditions (verified: `Block.if_` model.py:178-179 and `Block.while_` model.py:194-195 are the only construction sites), so a Rust compiler can emit `if let`/`while let` without model changes. The 13 items in Analysis 2's table are not blocking -- they're a checklist for the Rust compiler implementation.

### Whether the IIR "earns its keep"

Analysis 1 says yes: 2,305 lines reused, ~1,450 lines of duplication avoided. Analysis 2 questions whether the GSM itself could serve as the sole IR (Section 4.1, the "ANTLR approach"), eliminating IIR entirely. Analysis 3 doesn't take a position but notes that Option A (IIR reuse) is 3,650-4,950 total LoC vs Option B (full Rust reimplementation) at 10,350-13,500 LoC.

The tension is real: is reusing the IIR worth the coupling it creates (two compiler backends that must stay synchronized), or is it cleaner to have per-language generators reading GSM directly?

### Incremental delivery

Analysis 3 explicitly notes that Option A (new backend alongside Python) allows incremental delivery (parser first, unparser later), while Options B/C (Rust reimplementation) are much harder to deliver incrementally because you must port the IIR model and GSM before any generator code works.

Analysis 2's "Enhanced GSM" approach (Section 4.1) also allows incrementality -- you could write `gsm2parser_rs.py` without touching existing code -- but at the cost of duplicating generator logic.

---

## 3. Realistic Paths Forward

### Path 1: Add Rust IIR Compiler Backend (Analysis 1's recommendation, Analysis 3's Option A)

**What you build:**

| Component | Est. LoC | Language | Reuses |
|---|---|---|---|
| `fltk/iir/rust/compiler.py` | 350-450 | Python | Parallel to `py/compiler.py` (344 lines) |
| `fltk/iir/rust/reg.py` | ~30 | Python | Parallel to `py/reg.py` (29 lines) |
| Rust type registration in context | ~100 | Python | Extends `context.py` |
| `gsm2tree_rs.py` or refactored `gsm2tree` | 200-400 | Python | Parallel to `gsm2tree.py` (303 lines) |
| PyO3 wrapper generator | 300-500 | Python | New |
| Drivers/plumbing | ~200 | Python | Extends existing |
| Rust parser runtime | 600-900 | Rust | Reimplements `pyrt/` (396 lines) |
| Rust unparser runtime | 1,500-2,000 | Rust | Reimplements unparse runtime (1,144 lines) |
| **Total new** | **3,280-4,580** | | |

**What stays untouched:** `model.py` (779), `typemodel.py` (123), `gsm2parser.py` (756), `gsm2unparser.py` (1,549), `py/compiler.py` (344), `py/reg.py` (29) = 3,580 lines unchanged.

**Key risk:** Dual maintenance. Every IIR model evolution (new node type, changed semantics) requires updating both `py/compiler.py` and `rust/compiler.py`. Analysis 1 notes this is mitigated by the model being stable -- no model changes have been needed for the unparser addition.

**Other risks:**
- PyO3 nested enum classes. CST `Label` enums are nested inside node classes (`Rule.Label.NAME`). PyO3 doesn't natively support nested `#[pyclass]`. Workaround: standalone Rust enum + `#[classattr]` attachment. Flagged by explore-cst-interface.md Section 10.
- `children: list[tuple[Label|None, Union[...]]]`. The heterogeneous child list requires `PyObject` boxing in Rust. Consumers do direct indexing (`children[0][0]`), slicing (`children[::2]`), `len()`, and `isinstance()` on elements. All must work identically through PyO3.
- Lifetime annotations. `RefType.BORROW` has no lifetime name. Whether Rust parser methods need `&'a str` for terminal source is TBD. Analysis 1 flags this as open question #2.

**Delivery path:** Parser CST nodes first (simplest, most visible speedup), then parser runtime + generated parser, then unparser runtime + generated unparser. Each step is independently testable.

### Path 2: Per-Language Generators From GSM (Analysis 2's Section 4.1, "ANTLR approach")

**What you build:**

| Component | Est. LoC | Language | Replaces |
|---|---|---|---|
| `gsm2parser_rs.py` | ~750 | Python | Parallel to `gsm2parser.py` (756 lines) |
| `gsm2tree_rs.py` | ~300 | Python | Parallel to `gsm2tree.py` (303 lines) |
| `gsm2unparser_rs.py` | ~1,500 | Python | Parallel to `gsm2unparser.py` (1,549 lines) |
| PyO3 wrapper generation (integrated) | ~300 | Python | Built into above generators |
| Drivers | ~200 | Python | New |
| Rust parser runtime | 600-900 | Rust | Same as Path 1 |
| Rust unparser runtime | 1,500-2,000 | Rust | Same as Path 1 |
| **Total new** | **5,150-5,950** | | |

**What stays untouched:** All existing Python code. Zero changes to any file.

**Key risk:** ~2,550 lines of generator logic duplicated. The structural decisions in `gsm2parser.py` (method decomposition, memoization wiring, separator handling, quantifier logic, inline handling) and `gsm2unparser.py` (accumulator threading, trivia processing, anchor operations, suppressed item handling) must be re-implemented in the Rust-emitting generators. Analysis 2 estimates ~60% of the current generators is IIR node construction (duplicated only in form, not logic), and ~40% is structural decisions (truly duplicated logic).

**Advantage:** No coupling between Python and Rust backends. Each evolves independently. If the Python backend is eventually dropped, the Rust generators are self-contained.

**Delivery path:** Same incremental path as Path 1. Each generator is independent.

### Path 3: Hybrid -- Shared "Codegen Plan" + Thin Backends (Analysis 2's Section 4.5)

Extract the structural decisions from `gsm2parser.py` and `gsm2unparser.py` into a shared "codegen plan" data structure (lists of `ParserFn`, `UnparserFn`, term-consumption specs, separator specs), then have thin per-language backends that render the plan to source code.

**What you build:**

| Component | Est. LoC | Language | Notes |
|---|---|---|---|
| Codegen plan data model | 200-400 | Python | Extracts from gsm2parser/gsm2unparser |
| Plan builders (refactored generators) | ~2,000 | Python | Refactors existing 2,305 lines |
| Python plan renderer | 400-600 | Python | Replaces IIR + py/compiler path |
| Rust plan renderer | 400-600 | Python | New |
| PyO3 wrapper generation | 300-500 | Python | New |
| Rust runtimes | 2,100-2,900 | Rust | Same as above |
| **Total new/modified** | **5,400-7,000** | | |

**Key risk:** Significant refactoring of working code (`gsm2parser.py` and `gsm2unparser.py`) with no immediate functional benefit. The plan abstraction must capture every structural decision (left-recursion handling, trivia recursion guards, inline-to-parent, formatter anchor operations) correctly for both backends.

**Advantage:** Cleanest long-term architecture. No duplicated structural logic. New backends (e.g., JavaScript) would be thin renderers.

**Delivery path:** Hardest to deliver incrementally. Must refactor existing generators before any Rust output works.

### Path 4: Full Rust Reimplementation (Analysis 3's Option B/C)

Rewrite everything in Rust: GSM model, generators, IIR (or equivalent), both backends, runtimes.

| Component | Est. LoC | Notes |
|---|---|---|
| All generators + IIR + backends | 7,850-10,600 Rust | Replaces ~5,800 lines Python |
| Runtimes | 2,100-2,900 Rust | Same as above |
| fmt_config | 1,000-1,300 Rust | Replaces 833 lines Python |
| **Total** | **10,950-14,800 Rust** | |

**Key risk:** Enormous. Bootstrap complexity: you need a Rust `.fltkg` parser before you can generate anything. The Python IIR proxy builder pattern (`SelfExpr().fld.terminalsrc.method.consume_literal.call(...)`) used at ~120 call sites in generators relies on Python's `__getattr__` magic -- no Rust equivalent exists. Every call site becomes explicit builder calls.

**Advantage:** Single-language codebase. No Python-Rust interface at the generator level (only at the PyO3 output level).

**Delivery path:** Near-impossible to deliver incrementally. Must reach critical mass before anything works.

---

## 4. Key Numbers Summary

| Metric | Path 1 (IIR backend) | Path 2 (Per-lang gen) | Path 3 (Plan + renderer) | Path 4 (Full Rust) |
|---|---|---|---|---|
| New/modified LoC | 3,280-4,580 | 5,150-5,950 | 5,400-7,000 | 10,950-14,800 |
| Existing code touched | ~200 lines | 0 lines | ~2,300 refactored | 0 (full replacement) |
| Generator logic duplicated | None | ~2,550 lines | None | N/A |
| Dual maintenance burden | 2 compiler backends | 2 generator sets | 2 renderers | None |
| Incremental delivery | Easy | Easy | Hard | Very hard |
| New language cost (future) | ~500 LoC compiler | ~2,550 LoC generators | ~500 LoC renderer | N/A |

---

## 5. Cross-Cutting Risks and Open Questions

### PyO3 CST interface fidelity

The CST interface requirements are strict and specific (explore-cst-interface.md Section 10):

1. **Nested enum classes:** `Rule.Label.NAME` accessed as class attribute. PyO3 has no native nested `#[pyclass]`. Needs workaround.
2. **Heterogeneous `children` list:** `list[tuple[Label|None, Union[...]]]` with direct indexing, slicing, striding (`children[::2]`), `len()`, `isinstance()` on elements. Must present as a real Python list of real Python tuples.
3. **Mutable nodes:** CST nodes are not frozen (parser appends children incrementally). But `Span` is frozen with `eq=True`. A Rust Span behind PyO3 needs `__eq__`/`__hash__`.
4. **`children_foo()` returns a generator object.** Callers do both `for x in node.children_foo()` and `list(node.children_foo())`. PyO3 must return a proper Python iterator.
5. **`isinstance(child, SomeNodeClass)` in consumer code.** Works with PyO3 `#[pyclass]` if type registration is correct, but each CST node class must be a distinct `#[pyclass]`.

These constraints are identical across all four paths. The implementation difficulty is in the PyO3 wrapper layer, not the IR or generator choice.

### The `op="is"` special case

`gsm2unparser.py:977` emits `BinOp(op="is", lhs=child_label, rhs=LiteralNull())` for Python identity comparison. This compiles to `child_label is None` in Python. Rust has no identity comparison for `Option`-like types. The Rust compiler must pattern-match on `BinOp` with `op="is"` and `rhs=LiteralNull()` to emit `.is_none()` or `matches!(x, None)`. This is a concrete case where `BinOp.op` as a raw string creates fragility -- the Rust compiler must know about every Python-specific operator string.

All such strings found in producers: `"=="` (model.py:760), `">"` (model.py:750), `"-"` (model.py:755), `"and"` (model.py:742), `"or"` (model.py:747), `"is"` (gsm2unparser.py:977). The last is the only one without an IIR subclass -- it uses raw `BinOp` directly.

### Unparser runtime complexity

The unparser runtime (1,144 lines, especially `resolve_specs.py` at 539 lines) is substantially more complex than the parser runtime. The sliding-window pattern matcher in `resolve_specs.py:204-287` handles 7 mutator patterns with a deque. The Wadler-Lindig renderer (`renderer.py:47-170`) has subtle mode-switching logic. `fmt_config.py` (833 lines) has a complex CST-to-config transformation. These must all be reimplemented in Rust and produce identical output.

**Risk calibration:** If you want parser-only initially (no unparser), the runtime cost drops from ~2,100-2,900 to ~600-900 lines of Rust. The unparser can be deferred significantly.

### Global `_type_registry` (typemodel.py:36)

All three analyses flag this. Every `Type.__post_init__` self-registers into a module-level global dict. The duplicate-registration check is commented out (typemodel.py:80-82: `pass` instead of raise). In a multi-backend scenario, both Python and Rust compilation contexts share this global. Currently safe because type identity is shared, but the silent duplicate handling is a latent correctness risk.

### `Invocation`/`Expression`/`Add` in GSM

`gsm.Invocation` (gsm.py:249-256) and `gsm.Expression` (gsm.py:259) exist in the GSM data model but raise `NotImplementedError` in both `gsm2parser.py:308-309` and `gsm2tree.py:246-257`. Any Rust backend inherits this limitation. Not a blocker, but worth noting that the GSM has unused extensibility surface.

### Test coverage of generated code

12,539 lines of tests exist. These test the Python-generated parser and unparser behavior. A Rust backend must produce code that passes the same behavioral tests. The test infrastructure uses `plumbing.py` which dynamically `exec()`s generated Python -- testing Rust-generated code requires either a parallel test harness or integration through PyO3 wrappers.

---

## 6. Corrections and Observations Across Analyses

### Line count discrepancy

Analysis 3 says "Grand Total Hand-Written Source: ~8,444 lines." Actual total of the files it lists: 7,260 lines (verified by `wc -l`). The difference: Analysis 3 includes `plumbing_types.py` (42), `genparser.py` (224), `genunparser.py` (168), `fltk2gsm.py` (130), `bootstrap2gsm.py` (122), `bootstrap.py` (498) = 1,184 lines that aren't in my `wc -l` run. Total with those: 8,444. The number is correct; it's an accounting of different file sets.

### Analysis 2's "heavily Python-flavored" framing is overstated

Analysis 2 lists 13 Python-specific aspects of the IIR (Section 3). Analysis 1 audits each one and shows 0 require model changes. The "heavily Python-flavored" characterization applies to the compiler output, not the model. The model's abstractions (`Success`/`Failure`, `IsEmpty`, `IsInstance`, `SelfExpr`, `LetExpr`) are semantic concepts that happen to have been named with Python idioms but map naturally to Rust (`Option<T>`, `.is_empty()`, enum matching, `&self`, `if let`).

### Analysis 2 underweights the proxy builder API cost

Analysis 2's "Enhanced GSM" approach (Section 4.1) glosses over the proxy builder pattern. `gsm2parser.py` uses chains like `iir.SelfExpr().fld.packrat.method.apply.call(...)` at ~40 call sites, and `gsm2unparser.py` at ~80 call sites. These chains construct nested `FieldAccess`/`MethodAccess`/`MethodCall` IIR nodes in a single expression. Replacing this with direct Rust-source-string construction in per-language generators would be verbose and error-prone -- exactly the problem the IIR was designed to solve.

### Missing from all analyses: PyO3 build/packaging complexity

None of the three analyses discuss the build system integration. The current project uses setuptools + Bazel. Adding Rust + PyO3 requires either `maturin` or `setuptools-rust`, plus a Cargo workspace, plus CI changes. This is non-trivial operational overhead orthogonal to the codegen architecture.

### Missing from all analyses: Performance characterization

The stated goal is "Rust speed." No analysis quantifies the current Python performance bottleneck or estimates the speedup. If parsing/unparsing time is dominated by the Wadler-Lindig renderer or `resolve_specs` pattern matching, the unparser runtime is the priority. If it's dominated by the packrat memoization, the parser runtime matters more. If it's dominated by CST node construction and `children` list manipulation, PyO3 overhead might eat the Rust speedup.

### Missing from all analyses: What "near-identical CST dataclass interfaces" costs in practice

The constraint that Rust CST nodes present "near-identical" Python interfaces via PyO3 means every child access crosses the Python-Rust boundary. If consumers iterate `children` in Python, each element must be converted to a Python object. This could negate performance gains for workloads that are consumer-bound rather than parser-bound. A pure-Rust consumer API (without PyO3 wrapping) might be needed for actual speedup.
