# IIR Adaptation for Rust Code Generation -- Analysis

All claims below verified against source code, not Sonnet reports. File paths relative to repo root.

---

## 1. Current Architecture: What the IIR Is and Does

The IIR is ~1421 lines across 5 files:

| File | Lines | Role |
|---|---|---|
| `fltk/iir/typemodel.py` | 123 | `Type`, `TypeKey`, `TypeParam`, `ValueParam`, global `_type_registry` |
| `fltk/iir/model.py` | 779 | All expression, statement, class, function, scope, variable nodes |
| `fltk/iir/context.py` | 146 | `CompilerContext`, `TypeRegistry`, `create_default_context()` |
| `fltk/iir/py/compiler.py` | 344 | IIR-to-Python-AST compiler |
| `fltk/iir/py/reg.py` | 29 | `TypeInfo`, `Module` (Python import path info) |

The IIR is consumed by two producers and one consumer:

- **Producer: `gsm2parser.py`** (756 lines, 131 `iir.*` references) -- builds an `iir.ClassType` representing the entire parser class with all methods, fields, blocks, and expressions.
- **Producer: `gsm2unparser.py`** (1549 lines, 229 `iir.*` references) -- same pattern for the unparser class.
- **Consumer: `py/compiler.py`** (344 lines) -- walks the IIR graph, emitting Python `ast` nodes via `pygen` helpers.

A third codegen path (`gsm2tree.py` / CST node classes) does NOT use IIR for code structure -- only `iir.Type.make()` for type identity / registry lookup. It emits Python `ast` directly via `pygen`.

---

## 2. Verification of Key Claims From Sonnet Reports

### Confirmed

1. **`gsm2parser.py` uses IIR exclusively, never `pygen` directly.** Verified: zero imports of `pygen` in `gsm2parser.py`.

2. **`gsm2tree.py` uses `pygen` directly, not IIR for code structure.** Verified: only IIR references are `iir.Type` and `iir.context` for type registry. All class/method bodies built via `pygen.stmt()`, `pygen.function()`, etc.

3. **`RefType` is annotated in producers but ignored by compiler.** Verified: `py/compiler.py` contains exactly one `RefType` reference (line 149, inside `compile_class` for field init), and that reference constructs an `iir.Var` with `RefType.VALUE` -- it never branches on `ref_type` values. Meanwhile, `gsm2parser.py` uses `OWNING`, `BORROW`, `VALUE` and `gsm2unparser.py` uses `BORROW`, `VALUE` throughout.

4. **`LetExpr` is Python-specific (walrus operator).** Verified: `py/compiler.py:272-273` and `280-281` emit `(var := expr)` syntax. The IIR node itself (`model.py:776-779`) has `result: Expr` and `var: Var` with no language-neutral lowering.

5. **Operator strings are Python keywords.** Verified: `LogicalAnd.op="and"` (model.py:742), `LogicalOr.op="or"` (model.py:746). `LogicalNegation` compiles to `not (x)` (compiler.py:342).

6. **`SelfExpr` compiles to the string `"self"`.** Verified: compiler.py:296.

7. **`Success` is transparent; `Failure` is `None`.** Verified: compiler.py:319-321. No wrapping for Success; Failure returns `"None"`.

8. **`IsEmpty` compiles to `len(x) == 0`.** Verified: compiler.py:334.

9. **`IsInstance` compiles to `isinstance(x, T)`.** Verified: compiler.py:338-339.

10. **Bug in `compile()` at module level.** Verified: compiler.py:24-25 -- `raise NotImplementedError` is unconditionally reached after two `if` checks (no `continue`/`elif`). This function is not called by any current code path (callers use `compile_class` directly).

### Corrected / Nuanced

1. **`elif` chains.** The report says `compiler.py:266` raises `NotImplementedError` for `elif`. Verified at compiler.py:266-267: correct, but the producers never generate `elif` chains (they use nested `if_` with `orelse=True` only for `else` blocks, not chained `elif`).

2. **`gsm2unparser.py` "never writes a Python string or ast node directly".** Partially correct: the `generate_unparser()` function (lines 1531-1547) does return a list of `ast.Import`/`ast.ImportFrom` nodes constructed directly, not through IIR. The method/class bodies go through IIR.

---

## 3. What the IIR Actually Buys

The IIR serves as a **typed imperative code graph** that separates code-structure construction (done by `gsm2parser`/`gsm2unparser`) from target-language emission (done by `py/compiler`).

### Concrete value provided today

1. **Builder API with fluent proxy chains.** `FieldLookupProxy` and `MethodLookupProxy` (model.py:606-627) allow generators to write:
   ```python
   iir.SelfExpr().fld.terminalsrc.method.consume_literal.call(pos=..., literal=...)
   ```
   This constructs a `MethodCall(MethodAccess(FieldAccess(SelfExpr, "terminalsrc"), "consume_literal"), args)` in one expression. Without IIR, generators would construct Python AST nodes directly (much more verbose) or emit raw strings (unsafe, no structure).

2. **Type system with parameterization.** `Type.instantiate()` (typemodel.py:85-91) supports `GenericImmutableSequence.instantiate(value_type=SomeType)`. The `TypeRegistry` maps these to language-specific annotations. This parameterization is language-neutral.

3. **Scope management.** `Scope` (model.py:81-106) with `define`/`lookup` prevents name collisions. `Block.var()` auto-defines into scope and appends `VarDef` (model.py:134-146).

4. **Structural validation.** `ClassType` enforces constructor uniqueness (model.py:556-558), tracks fields/methods by name (model.py:496-515), and validates parent-block consistency (compiler.py:188-192, 202-206).

---

## 4. Node-by-Node Adaptation Requirements for Rust

### Nodes that translate directly (minimal/no IIR change needed)

These IIR nodes have near-1:1 Rust equivalents. The compiler translates them differently, but the IIR model node stays the same:

| IIR Node | Python emission | Rust emission |
|---|---|---|
| `Var`, `VarByName` | `name` | `name` (+ `let`/`let mut` at def site) |
| `VarDef` | `name: T = init` | `let name: T = init;` |
| `AssignStatement` | `target = expr` | `target = expr;` |
| `Return` | `return expr` | `return expr;` or trailing expr |
| `Break` | `break` | `break;` |
| `If` | `if cond:` | `if cond {` |
| `WhileLoop` | `while cond:` | `while cond {` |
| `Block` | indented block | `{ ... }` |
| `ExprStatement` | `expr` | `expr;` |
| `BinOp` (with `==`, `>`, `-`) | `(lhs) op (rhs)` | `(lhs) op (rhs)` |
| `Subscript` | `target[index]` | `target[index]` |
| `LiteralString` | `repr(value)` | `"value".to_string()` or `&str` |
| `LiteralInt` | `repr(value)` | `value` with type suffix |
| `LiteralNull` | `None` | `None` (inside `Option`) |
| `LiteralSequence` | `[e1, e2]` | `vec![e1, e2]` |
| `LiteralMapping` | `{k: v}` | `HashMap::from([(k, v)])` |
| `MemberAccess` | `obj.member` | `obj.member` |
| `MethodCall` | `obj.method(args)` | `obj.method(args)` |
| `BoundMethod` | `obj.method` | closure or fn pointer |
| `Construct` | `TypeName(args)` | `TypeName::new(args)` or struct literal |
| `Field`, `FieldAccess` | `self.field` | `self.field` |
| `Store` | assignment target | `&mut` target |
| `Load`, `Move` | transparent | `.clone()` or move semantics |

### Nodes requiring semantic translation (IIR model OK, compiler must reinterpret)

| IIR Node | Python | Rust | IIR change? |
|---|---|---|---|
| `SelfExpr` | `"self"` | `&self`/`&mut self` | No -- `Method.mutable_self` already exists (model.py:451) |
| `Success(type, expr)` | transparent `expr` | `Some(expr)` | No -- compiler wraps |
| `Failure(type)` | `None` | `None` | No -- Rust compiler emits `None` inside `Option<T>` |
| `IsEmpty(expr)` | `len(x) == 0` | `x.is_empty()` | No |
| `IsInstance(expr, typ)` | `isinstance(x, T)` | `matches!()` or enum match | No model change if limited to known CST node types |
| `LogicalNegation` | `not (x)` | `!(x)` | No |
| `LogicalAnd`, `LogicalOr` | `and`, `or` | `&&`, `\|\|` | No model change; `op` field is only read by compiler |

**Note on `BinOp.op` as raw string:** `LogicalAnd` defaults `op="and"`, `LogicalOr` defaults `op="or"` (model.py:740-746). The Python compiler reads `expr.op` verbatim (compiler.py:302). A Rust compiler can pattern-match on the subclass (`LogicalAnd`, `LogicalOr`) and ignore `op`, which is already the approach for `LogicalNegation` at compiler.py:341-342.

### Nodes requiring IIR model changes or new nodes

| Issue | Detail | Severity |
|---|---|---|
| **`LetExpr` (walrus)** | model.py:776-779. Python: `(var := expr)`. Rust: `if let Some(var) = expr`. All current uses wrap `LetExpr` in `If` or `WhileLoop` conditions (verified: `Block.if_` at model.py:178-179 and `Block.while_` at model.py:194-195 are the only construction sites). **No model change needed** -- Rust compiler can detect `LetExpr` inside `If`/`WhileLoop` condition and emit `if let`/`while let`. |
| **`kwargs` in `Construct`/`MethodCall`** | model.py:305, 398. Rust has no keyword arguments. Rust compiler maps kwarg names to positional args or struct fields. **No model change needed** -- kwargs already carry names. |
| **Constructor pattern** | `Constructor` (model.py:639-642) with `init_list`. Python emits `__init__`. Rust needs `fn new() -> Self` with struct literal. `init_list` maps well to `Self { field1: param1, field2: expr2 }`. **No model change.** |
| **Multiple inheritance** | `ClassType.base_classes` (model.py:467). Neither `gsm2parser` nor `gsm2unparser` sets this -- both default to `()` (model.py:490). **Not a problem.** |
| **`EnumType`** | model.py:645-676. Neither producer creates `EnumType` via IIR. `gsm2tree.py` creates enums via `pygen` directly. **Not relevant to IIR-based codegen.** |
| **`RefType` enum** | model.py:234-241. Currently decorative. Generators already annotate sensibly: params use `BORROW`, locals use `VALUE`. **A Rust backend makes this information meaningful for free.** |

---

## 5. The `CompilerContext` and Type Registry

`CompilerContext` (context.py:42-47) currently holds `python_type_registry: TypeRegistry` (mapping `TypeKey` to `pyreg.TypeInfo(module, name, concrete_name)`) and `capture_trivia: bool`.

For Rust, add a parallel `rust_type_registry` mapping `TypeKey` to Rust-specific type info. `TypeInfo` (reg.py:20-29) is Python-specific (has Python import paths). A Rust `TypeInfo` needs: crate path, type name, whether `Box`/`Arc` wrapping is needed, lifetime parameters.

The global `_type_registry` (typemodel.py:36) is for type identity/interning only, not backend-specific. No changes needed.

---

## 6. The `gsm2tree.py` Problem: Outside IIR

`gsm2tree.py` (303 lines, CST node class generation) bypasses IIR entirely. It builds Python `ast` nodes via `pygen` string snippets.

Consequences:
- **A Rust backend for CST nodes cannot reuse `gsm2tree.py`.** You need either a parallel `gsm2tree_rs.py` or a refactoring of `gsm2tree.py` to go through IIR.
- Since CST node classes are simpler than parser/unparser (dataclass-like structs with accessor methods), refactoring cost is moderate.
- `py_class_for_model()` (gsm2tree.py:109-244) does most of the work.

Two strategies:
1. **Refactor `gsm2tree` to emit IIR**, then compile IIR to both Python and Rust. Brings CST codegen into the same pipeline.
2. **Write a separate `gsm2tree_rs.py`** that directly emits Rust source. Mirrors current pattern. Faster to implement, doesn't touch working code, duplicates logic.

---

## 7. What a `rust/compiler.py` Would Look Like

A `fltk/iir/rust/compiler.py` would mirror `py/compiler.py`:

| Python compiler function | Rust equivalent |
|---|---|
| `compile_class` (77-169) | Emit `struct` + `impl` block. `init_list` -> struct literal in `fn new()`. |
| `compile_function` (172-198) | `fn name(&self, params) -> ReturnType { body }`. `&self`/`&mut self` from `Method.mutable_self`. |
| `compile_stmt` (213-246) | Same dispatch. `VarDef` -> `let [mut] name: Type = init;`. |
| `compile_expr` (294-344) | Same dispatch with Rust syntax. `Success` -> `Some(expr)`, `Failure` -> `None`, `IsEmpty` -> `.is_empty()`, `LogicalNegation` -> `!`, `LogicalAnd` -> `&&`, `LogicalOr` -> `\|\|`, `LetExpr` in If -> `if let Some(var) = expr`. |
| `iir_type_to_py_annotation` (49-74) | `iir_type_to_rust_type`: `Maybe[T]` -> `Option<T>`, `ImmutableSequence[T]` -> `Vec<T>`, `String` -> `String`, `IndexInt` -> `usize`. |

Estimated: ~350-450 lines.

---

## 8. IIR Nodes Used by Each Producer -- Full Inventory

**`gsm2parser.py` (31 distinct IIR symbols):**
Types: `Auto`, `Expr`, `IndexInt`, `Maybe`, `GenericImmutableSequence`, `GenericMutableHashmap`, `SignedIndexInt`, `String`, `Type`, `TYPE`.
Structural: `Block`, `ClassType`, `Method`, `Module`, `Param`.
Variables: `Var`, `VarByName`, `RefType`, `INIT_FROM_PARAM`.
Expressions: `Construct`, `Equals`, `Failure`, `LiteralInt`, `LiteralMapping`, `LiteralNull`, `LiteralSequence`, `LiteralString`, `SelfExpr`, `Subscript`, `Success`.

**`gsm2unparser.py` (34 distinct IIR symbols):**
All of above plus: `BinOp`, `Bool`, `Break`, `FalseBool`, `GenericMutableSequence`, `IsInstance`, `LogicalAnd`, `LogicalNegation`, `MethodAccess`, `MethodCall`, `TrueBool`.
Minus: `Equals`, `GenericImmutableSequence`, `GenericMutableHashmap`, `Failure`, `LiteralMapping`, `LiteralNull`, `Success`, `SignedIndexInt`.

**Handled by `py/compiler.py` but NOT used by either producer:**
`Function` (only `Method` used), `BoundMethod`, `UnaryOp`, `VarDefExpr`, `ClassDef`, `Constant` (only pre-built `TrueBool`/`FalseBool` singletons used).

---

## 9. Assessment: Adaptation Scope

### What changes in IIR model code (`typemodel.py` + `model.py`)

**Nothing mandatory.** Every IIR node used by the producers has a reasonable Rust interpretation without model changes. `RefType` annotations already present in generator code become meaningful in a Rust backend.

Optional improvements:
- Replace `BinOp.op: str` with an enum to avoid Python keyword strings in the model. Low priority since subclasses (`LogicalAnd`, etc.) encode operator semantics and a Rust compiler dispatches on subclass type.
- Add `ForLoop` if Rust codegen needs `for x in iter {}` (current generators use `while` with walrus).

### What changes in context/registry code

- New `RustTypeInfo` dataclass parallel to `pyreg.TypeInfo` (~30 lines).
- `rust_type_registry` field on `CompilerContext` or new `RustCompilerContext` (1 field).
- Register Rust type mappings for builtins/parser types (parallel to `_register_builtin_types`, ~70 lines).

### What's entirely new

- `fltk/iir/rust/compiler.py` (~350-450 lines, parallel to `py/compiler.py`).
- `fltk/iir/rust/reg.py` (~30 lines, Rust type info).
- Either `gsm2tree_rs.py` or refactored `gsm2tree.py` for IIR (~200-400 lines).

### What stays unchanged

- `typemodel.py` (123 lines) -- no changes.
- `model.py` (779 lines) -- no changes.
- `gsm2parser.py` (756 lines) -- no changes; already emits language-neutral IIR.
- `gsm2unparser.py` (1549 lines) -- no changes.
- `py/compiler.py` (344 lines) -- no changes.
- `py/reg.py` (29 lines) -- no changes.
- `context.py` (146 lines) -- small addition for Rust registry field.

---

## 10. Does the IIR Earn Its Keep?

### Before Rust

The IIR saves 2305 lines of generator code from being tightly coupled to Python syntax. The proxy-chain builder API (`self_expr.fld.packrat.method.apply.call(...)`) is substantially more readable than equivalent `ast.Call(ast.Attribute(...))` construction.

### After adding Rust

- 2305 lines of generator code (756 + 1549) are reused AS-IS for Rust output.
- Only ~500 lines of new compiler code needed (Rust compiler + type registry).
- Without IIR, you'd duplicate generator logic: 2305 x 2 backends = ~4600 lines, vs. 2305 shared + ~500 Rust compiler + ~350 Python compiler = ~3150 total.
- Savings: ~1450 lines of avoided generator duplication, plus single source of truth.

### The `gsm2tree` gap

The main architectural gap: `gsm2tree.py` bypasses IIR, so CST node codegen cannot benefit from multi-backend compilation unless refactored. This is the single largest piece of work needed to make IIR cover the entire codegen surface.

---

## 11. Open Factual Questions

1. **PyO3 wrapper generation.** Generated Rust structs need `#[pyclass]`, `#[pymethods]` attributes. The IIR has no notion of "decorators/attributes on classes" -- Python's `@dataclass` is added by `gsm2tree.py` directly, not via IIR. Where does PyO3 annotation logic live?

2. **Lifetime annotations.** Rust parsers likely need `&'a str` for terminal source. `RefType.BORROW` has no lifetime name. Whether the Rust compiler can infer lifetimes or the IIR needs a `Lifetime` concept is TBD.

3. **Error handling.** Current generators use `None`/`Success`/`Failure` (Option-like semantics). `Option<T>` is the natural Rust fit. If `Result<T, E>` is desired, `Success`/`Failure` need richer mapping.

4. **Global `_type_registry`.** `Type.__post_init__` (typemodel.py:73-83) silently handles duplicate keys (commented-out raise at line 80-82, replaced with `pass`). Latent correctness risk unrelated to Rust but relevant for multi-backend scenarios with different type-creation orders.

5. **`Invocation`/`Expression`/`Add` in GSM.** These GSM nodes (gsm.py:249-270) exist but are not implemented in `gsm2parser.py` or `gsm2tree.py` (both fall through to `NotImplementedError`). Any Rust backend shares this limitation.
