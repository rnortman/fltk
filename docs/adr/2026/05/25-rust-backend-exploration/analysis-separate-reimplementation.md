# Reimplementation Cost Analysis for Rust Backend

---

## Verified Line Counts (Hand-Written Source)

Excluding generated files (`fltk_parser.py`, `fltk_cst.py`, `*_trivia_parser.py`, `bootstrap_parser.py`, `bootstrap_cst.py`, `toy_*.py`, `unparsefmt_*.py`) and tests.

### Code Generation Generators (GSM -> IIR/AST)

| File | Lines | What it does |
|---|---|---|
| `fltk/fegen/gsm2parser.py` | 756 | GSM -> IIR ClassType for parser |
| `fltk/fegen/gsm2tree.py` | 303 | GSM -> Python AST for CST dataclasses (uses pygen, NOT IIR) |
| `fltk/unparse/gsm2unparser.py` | 1549 | GSM -> IIR ClassType for unparser |
| **Subtotal** | **2608** | |

### IIR (Intermediate Representation) System

| File | Lines | Role |
|---|---|---|
| `fltk/iir/model.py` | 779 | IIR node types: Expr, Statement, Class, Method, etc. |
| `fltk/iir/typemodel.py` | 123 | Parameterized type system with global registry |
| `fltk/iir/context.py` | 146 | CompilerContext, TypeRegistry, builtin type registration |
| `fltk/iir/py/compiler.py` | 344 | IIR -> Python AST (the ONLY language backend today) |
| `fltk/iir/py/reg.py` | 29 | Python type info (module path, name, concrete_name) |
| **Subtotal** | **1421** | |

### Runtime Support (shipped with generated code)

| File | Lines | Role |
|---|---|---|
| `fltk/fegen/pyrt/terminalsrc.py` | 68 | Span, TerminalSource (consume_literal, consume_regex) |
| `fltk/fegen/pyrt/memo.py` | 257 | Packrat memoization with left-recursion (seed-growing) |
| `fltk/fegen/pyrt/errors.py` | 71 | Error tracking and formatting |
| `fltk/unparse/combinators.py` | 253 | Doc algebra (Wadler-Lindig) |
| `fltk/unparse/accumulator.py` | 126 | Immutable Doc accumulator |
| `fltk/unparse/renderer.py` | 191 | Wadler-Lindig renderer |
| `fltk/unparse/resolve_specs.py` | 539 | Three-pass spacing resolution |
| `fltk/unparse/fmt_config.py` | 833 | Format config data model + CST-to-config |
| `fltk/unparse/pyrt.py` | 35 | UnparseResult, extract_span_text |
| **Subtotal** | **2373** | |

### Plumbing/Drivers

| File | Lines | Role |
|---|---|---|
| `fltk/pygen.py` | 124 | Python AST factory helpers |
| `fltk/plumbing.py` | 327 | Facade: wires grammar parse -> codegen -> exec |
| `fltk/plumbing_types.py` | 42 | ParserResult, ParseResult, UnparserResult |
| `fltk/fegen/genparser.py` | 224 | CLI driver for parser generation |
| `fltk/unparse/genunparser.py` | 168 | CLI driver for unparser generation |
| **Subtotal** | **885** | |

### GSM (Grammar Semantic Model)

| File | Lines | Role |
|---|---|---|
| `fltk/fegen/gsm.py` | 407 | Grammar data model + validation |
| `fltk/fegen/fltk2gsm.py` | 130 | Full CST -> GSM visitor |
| `fltk/fegen/bootstrap2gsm.py` | 122 | Bootstrap CST -> GSM visitor |
| `fltk/fegen/bootstrap.py` | 498 | Hand-written bootstrap grammar as Python data |
| **Subtotal** | **1157** | |

### Grand Total Hand-Written Source: ~8,444 lines

---

## Option A: Separate Rust Code Emitter (Python Generator, Rust Output)

**What stays the same:** GSM (407), gsm2parser.py (756), gsm2unparser.py (1549), IIR model (779), IIR typemodel (123). Total: 3,614 lines untouched.

**What must be written new:**

### A1. Rust backend for IIR compiler (~500-700 lines Python)

Replace `iir/py/compiler.py` (344 lines) with a Rust code emitter. The compiler is a straightforward pattern-match over ~25 IIR node types. A Rust emitter would be structurally identical but with different string templates.

Key translations required (verified against `iir/py/compiler.py`):
- `compile_expr` (line 294-344): 22 isinstance branches emitting Python strings. Each needs a Rust equivalent.
- `compile_stmt` (line 213-246): 7 statement types.
- `compile_function` (line 172-198): params, `self` -> `&self`/`&mut self`.
- `compile_class` (line 77-169): constructor synthesis, field init.

Python-specific idioms in the IIR that need Rust translation (all verified):
- `LetExpr` walrus `:=` (model.py:776, compiler.py:272-281) -> Rust `if let`/`while let`
- `LogicalAnd.op="and"`, `LogicalOr.op="or"` (model.py:740-745) -> `&&`, `||`
- `LogicalNegation` "not" (compiler.py:342) -> `!`
- `Failure` -> `None` (compiler.py:319) -> `None` (works in Rust `Option`)
- `Success` transparent (compiler.py:321) -> `Some(expr)`
- `IsInstance` -> `isinstance()` (compiler.py:338) -> `matches!()` or enum match
- `IsEmpty` -> `len(x) == 0` (compiler.py:334) -> `.is_empty()`
- `LiteralNull` -> `None` (compiler.py:325) -> Rust `None`
- `BinOp.op` raw strings like `"is"` (gsm2unparser.py:977) -> not valid Rust; needs special handling

### A2. Rust type registry (~150 lines Python)

Analogous to `iir/context.py:76-147` (`_register_builtin_types`) and `iir/py/reg.py` (29 lines). Maps IIR types to Rust types: `Maybe` -> `Option<T>`, `GenericImmutableSequence` -> `Vec<T>`, `GenericMutableHashmap` -> `HashMap<K,V>`, `String` -> `String`, `IndexInt`/`SignedIndexInt` -> `usize`/`isize`, `Bool` -> `bool`.

### A3. Rust runtime library (~2100-2900 lines of Rust)

Must reimplement in Rust:
- `terminalsrc.py` (68 lines) -> ~100-150 lines Rust. Span is trivial; regex matching needs `regex` crate.
- `memo.py` (257 lines) -> ~400-600 lines Rust. The packrat memoization with left-recursion seed-growing (`Packrat.apply()` at memo.py:82-156) is the hardest piece. The `_recall`/`_setup_recursion`/`_grow_seed` triad must be translated faithfully.
- `errors.py` (71 lines) -> ~100-150 lines Rust.
- Unparser runtime: `combinators.py` (253), `accumulator.py` (126), `renderer.py` (191), `resolve_specs.py` (539), `pyrt.py` (35) = 1144 lines Python -> ~1500-2000 lines Rust (Rust tends to be ~1.3-1.7x Python for data-heavy code with pattern matching).

### A4. gsm2tree.py Rust variant (~400-500 lines Python)

`gsm2tree.py` (303 lines) does NOT use IIR for code structure. It builds Python `ast` nodes directly via `pygen` (imported at line 9, used extensively at lines 110-243). For Rust output, you need either:
- A new `gsm2tree_rs.py` that emits Rust struct definitions directly as strings (~400 lines Python), OR
- Refactor gsm2tree to use IIR (requires extending IIR for struct definitions, derive macros, etc.)

### A5. PyO3 wrapper generation (~300-500 lines Python)

If CST nodes must be accessible from Python, need a generator that emits `#[pyclass]`/`#[pymethods]` wrappers for each CST node. The interface contract is defined by gsm2tree.py:109-243: `children: list[tuple[Label|None, ChildUnion]]`, nested `Label` enum, typed accessors (`children_*`, `child_*`, `maybe_*`, `append_*`, `extend_*`).

### A6. Driver/plumbing adjustments (~200 lines Python)

### Option A Summary

| Component | Estimate (LoC) | Language |
|---|---|---|
| Rust IIR compiler backend | 500-700 | Python |
| Rust type registry | 150 | Python |
| gsm2tree Rust variant | 400-500 | Python |
| PyO3 wrapper generator | 300-500 | Python |
| Drivers/plumbing | 200 | Python |
| **Subtotal new Python** | **1,550-2,050** | |
| Rust runtime (parser) | 600-900 | Rust |
| Rust runtime (unparser) | 1,500-2,000 | Rust |
| **Subtotal new Rust** | **2,100-2,900** | |
| **Grand total new code** | **3,650-4,950** | |

**What you get:** Python generators unchanged. Add a new backend. Risk: every IIR evolution must be mirrored in both backends. gsm2tree must be forked or refactored.

---

## Option B: Reimplement the Generator Itself in Rust

Rewrite gsm2parser.py (756), gsm2tree.py (303), gsm2unparser.py (1549), plus the IIR system (model.py 779, typemodel.py 123, context.py 146), plus both backends (compiler.py 344 for Python, new for Rust), plus the GSM model (gsm.py 407), plus drivers.

| Python file | Lines | Rust estimate | Notes |
|---|---|---|---|
| `gsm.py` | 407 | 500-650 | Data model + validation. Straightforward. |
| `gsm2parser.py` | 756 | 1,000-1,300 | Heavy use of proxy chains (`SelfExpr().fld.x.method.y.call()`). |
| `gsm2tree.py` | 303 | 400-500 | Currently pygen-based; Rust version emits Rust structs via string templates. |
| `gsm2unparser.py` | 1549 | 2,000-2,600 | Largest generator. Same IIR builder pattern. |
| `iir/model.py` | 779 | 1,000-1,300 | ~50 node types, proxy builders. Rust enums natural fit. |
| `iir/typemodel.py` | 123 | 150-200 | Type parameterization + global registry. |
| `iir/context.py` | 146 | 200-250 | Type registry + builtin types. |
| Python backend (`compiler.py` + `reg.py`) | 373 | 450-600 | Must still emit Python for backward compat. |
| Rust backend (new) | 0 | 500-700 | New Rust emitter. |
| `pygen.py` | 124 | 150-200 | Only needed if still generating Python. |
| Drivers | 719 | 900-1,200 | CLI, wiring. |
| Parser runtime | 396 | 500-700 | terminalsrc + memo + errors |
| Unparser runtime | 1144 | 1,500-2,000 | combinators + accumulator + renderer + resolve_specs + pyrt |
| `fmt_config.py` | 833 | 1,000-1,300 | Config data model + CST-to-config. |
| **Total Python source** | **~7,652** | **~10,350-13,500 Rust** | |

---

## Option C: Rust Generator That Also Emits Python

Same as Option B, but the Rust generator replaces the Python generator entirely. Additional cost: the Python IIR compiler (`iir/py/compiler.py`, 344 lines) must be re-implemented inside the Rust codebase to emit Python source strings (~450-600 lines Rust). Plus gsm2tree Python emission (~400 lines Rust).

**Total: ~10,800-14,100 lines of Rust.**

---

## Key Structural Facts Affecting All Options

### gsm2tree.py bypasses IIR (verified)

`gsm2tree.py` imports `pygen` (line 9) and builds `ast.ClassDef`/`ast.FunctionDef` directly via `pygen.dataclass()`, `pygen.function()`, `pygen.stmt()` (lines 110-243). It does NOT build IIR `Method`/`Block` nodes. It only uses `iir.Type.make()` for type registry keys (line 75). For any multi-target approach, gsm2tree must either be forked per target or refactored to use IIR (which currently lacks `@dataclass` decorator support, nested class support, and generator expression support).

### gsm2parser.py and gsm2unparser.py are IIR-only (verified)

`gsm2parser.py` has zero imports from `pygen` (verified by inspection). `gsm2unparser.py` similarly builds IIR only (line 52), except for the module-level import list at lines 1531-1547 which are raw `ast.Import` nodes.

### The IIR has Python-specific operators baked in (verified)

`BinOp.op` is a raw string. `LogicalAnd` defaults to `op="and"` (model.py:742), `LogicalOr` to `op="or"` (model.py:747). `gsm2unparser.py` uses `op="is"` (line 977) for identity comparison. A Rust backend must special-case all of these.

### fmt_config.py is pure data model (833 lines, verified)

Language-agnostic in principle. Has a complex CST visitor (lines 328-833) parsing `.fltkfmt` format files. Would need porting in Options B/C.

### Packrat memoization with left-recursion is the hardest runtime piece (verified)

`memo.py:77-156` implements `Packrat.apply()` with `_recall`, `_setup_recursion`, `_grow_seed`. ~80 lines of dense state-machine logic.

### IIR proxy builder pattern is Python-magic-heavy (verified)

`FieldLookupProxy.__getattr__` (model.py:611-617) and `MethodLookupProxy.__getattr__` (model.py:624-627) use `__getattr__` to create nodes on-the-fly. Usage like `iir.SelfExpr().fld.terminalsrc.method.consume_literal.call(...)` (gsm2parser.py:122-125). In Rust, this becomes explicit builder calls. Touches ~40 call sites in gsm2parser.py and ~80 in gsm2unparser.py.

---

## Comparison Matrix

| | Option A: Separate Backend | Option B: Rust Generator | Option C: Rust Gen + Python Emit |
|---|---|---|---|
| **New Python LoC** | 1,550-2,050 | 0 | 0 |
| **New Rust LoC** | 2,100-2,900 | 10,350-13,500 | 10,800-14,100 |
| **Total new LoC** | 3,650-4,950 | 10,350-13,500 | 10,800-14,100 |
| **Existing code modified** | ~200 lines (plumbing) | 0 (full replacement) | 0 (full replacement) |
| **Dual maintenance** | Yes (IIR evolution x2) | No (Rust only) | No (Rust only) |
| **gsm2tree story** | Fork or refactor | Rewrite in Rust | Rewrite in Rust |
| **Bootstrap complexity** | Low (Python bootstrap unchanged) | High (need Rust .fltkg parser first) | Highest |
| **Can retire Python generators** | No | Yes (after port) | Yes (after port) |
| **Incremental delivery** | Yes (parser first, unparser later) | Hard (must port IIR + gsm first) | Hardest |

---

## Open Factual Questions

1. **What subset of IIR node types does gsm2unparser.py actually use?** Some node types in model.py (e.g., `VarDefExpr`, `EnumType`, `UnaryOp`) may not be exercised. A precise usage audit would reduce the Rust backend scope.

2. **Does the `op="is"` usage in gsm2unparser.py:977 appear in generated output?** If it does, the Rust IIR compiler must handle identity comparison, which has no direct Rust equivalent.

3. **What is the test coverage of generated code behavior?** The test suite is 12,539 lines; its coverage of generated parser/unparser behavior determines how much regression testing a Rust backend needs.

4. **Generated output sizes for reference:** The fltk grammar produces 1,260 + 1,279 + 1,127 = 3,666 lines. The unparsefmt grammar produces 2,929 + 3,013 + 2,728 = 8,670 lines. These indicate the generated Rust code volume to expect.
