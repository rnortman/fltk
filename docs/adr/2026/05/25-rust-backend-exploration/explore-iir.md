# IIR (Imperative Intermediate Representation) Investigation

All facts below are anchored to file:line in `fltk/iir/`.

---

## 1. IIR Node Types

### Type System Nodes (`typemodel.py`)

- **`Type`** (`typemodel.py:50`) — Base class for all IIR types. Fields: `cname: str|None`, `params: Mapping[str,ParamType]`, `instantiates: Optional[Type]`, `arguments: Mapping[str,Argument]`. Auto-computes `key: TypeKey` on init and registers in a global `_type_registry` dict keyed by `TypeKey`.
- **`TypeKey`** (`typemodel.py:29`) — Frozen dataclass used as a hashable identity for a `Type`. Fields: `cname`, `params` (tuple), `instantiates` (TypeKey|None), `arguments` (tuple).
- **`ParamType`** (`typemodel.py:7`) — Abstract base for type parameters.
- **`TypeParam`** (`typemodel.py:11`) — A type parameter with optional bound (`bound: Optional[Type]`). The constant `TYPE = TypeParam(bound=None)` is the unconstrained type parameter.
- **`ValueParam`** (`typemodel.py:19`) — A value-level parameter holding a type (`value_type: Type`).

### Built-in Types (`model.py:21-48`)

- **`Void`** — `Type.make(cname="Void")` — absence of value.
- **`Auto`** — `Type.make(cname="Auto")` — type inference marker; triggers untyped variable declaration in Python output.
- **`PrimitiveType`** (`model.py:27`) — Subclass of `Type` for numeric primitives; treated specially by compiler (no annotation lookup for constructor).
- **`UInt64`** — `PrimitiveType.make(cname="uint64")` — 64-bit unsigned int.
- **`IndexInt`** — `PrimitiveType.make(cname="IndexInt")` — index/offset integer; maps to Python `int`.
- **`SignedIndexInt`** — `PrimitiveType.make(cname="SignedIndexInt")` — signed index integer; maps to Python `int`.
- **`Bool`** — `PrimitiveType.make(cname="bool")`.
- **`String`** — `Type.make(cname="string")` — maps to Python `str`.
- **`Maybe`** — `Type.make(cname="Maybe", params={"value_type": TYPE})` — optional/nullable type; maps to `typing.Optional`.
- **`GenericImmutableSequence`** — `Type.make(cname="ImmutableSequence", params={"value_type": TYPE})` — maps to `typing.Sequence` with concrete name `list`.
- **`GenericMutableSequence`** — `Type.make(cname="MutableSequence", params={"value_type": TYPE})` — defined but NOT registered in `context.py`.
- **`GenericImmutableHashmap`** — `Type.make(cname="ImmutableHashmap", params={"key_type":TYPE,"value_type":TYPE})` — defined but NOT registered.
- **`GenericMutableHashmap`** — `Type.make(cname="MutableHashmap", params={"key_type":TYPE,"value_type":TYPE})` — maps to `collections.abc.MutableMapping` with concrete name `dict`.

### Structural Types (`model.py`)

- **`ClassType`** (`model.py:462`) — A user-defined class. Fields: `defined_in: Module`, `block: Block`, `doc: str|None`, `base_classes: Sequence[Type]`, `constructor: Optional[Constructor]`. Carries its own `Scope` inside `block`.
- **`EnumType`** (`model.py:645`) — An enum type. Fields: `defined_in: Module`, `doc: str|None`, `fields: MutableSequence[str]`. Fields are plain strings (names only, no values).

### Scope/Block Nodes

- **`Scope`** (`model.py:81`) — A dictionary-backed name→Nameable mapping with optional parent for lexical scoping. Methods: `define`, `lookup` (with `recursive` flag), `lookup_as`.
- **`Block`** (`model.py:110`) — A sequence of statements with an optional `inner_scope: Scope|None`. Helper methods emit and append statements: `var`, `assign`, `expr_stmt`, `if_`, `while_`, `return_`.
- **`Module`** (`model.py:207`) — Top-level container with `name: str`, `scope: Scope`, `block: Block`. Factory: `Module.make(name)`.

### Variable Nodes

- **`RefType`** (`model.py:234`) — Enum: `VALUE=0`, `BORROW=1`, `MUT_BORROW=2`, `OWNING=3`, `SHARED=4`, `SELF=5`. Annotates how a variable is held; all but `VALUE` are semantically inert in the Python compiler (not used in output).
- **`ValRef`** (`model.py:244`) — Abstract base for anything that can be loaded/stored/moved. Methods: `.load()`, `.load_mut()`, `.store()`, `.move()` — each returns the corresponding expression wrapper.
- **`Var`** (`model.py:261`) — A local variable or parameter. Fields: `name: str`, `typ: Type`, `ref_type: RefType`, `mutable: bool`.
- **`VarByName`** (`model.py:268`) — Subclass of `Var`; compiler treats identically (emits `expr.name`).
- **`Field`** (`model.py:407`) — A class field. Extends `Var` with `in_class: ClassType`, `init: Expr|None`.
- **`Param`** (`model.py:422`) — A function/method parameter. Extends `Var`.

### Statement Nodes (`model.py:683-716`)

- **`Statement`** (`model.py:70`) — Abstract base. Field: `parent_block: Optional[Block]`.
- **`Block`** (`model.py:110`) — Also a statement (sequence of statements with scope).
- **`VarDef`** (`model.py:274`) — Variable declaration statement. Fields: `var: Var`, `init: Expr|None`.
- **`AssignStatement`** (`model.py:697`) — Assignment. Fields: `target: Expr`, `expr: Expr`.
- **`Return`** (`model.py:703`) — Return statement. Field: `expr: Expr`.
- **`Break`** (`model.py:708`) — Break from a loop. No fields beyond `parent_block`.
- **`ExprStatement`** (`model.py:712`) — Expression used as a statement. Field: `expr: Expr`.
- **`If`** (`model.py:683`) — Conditional. Fields: `condition: Expr`, `block: Block`, `orelse: Union[If,Block]|None`. `orelse` allows elif chains (though the compiler raises `NotImplementedError` for `elif` at `py/compiler.py:266`).
- **`WhileLoop`** (`model.py:691`) — While loop. Fields: `condition: Expr`, `block: Block`.
- **`ClassDef`** (`model.py:601`) — Module-level class definition statement. Field: `klass: ClassType`.

### Expression Nodes (`model.py`)

- **`Expr`** (`model.py:55`) — Abstract base. Properties: `.fld` → `FieldLookupProxy`, `.mut_fld` → `FieldLookupProxy(mutable=True)`, `.method` → `MethodLookupProxy`.
- **`VarDef`/`VarDefExpr`** (`model.py:280`) — Expression form of variable definition: `var: Var`, `init: Expr`. (Not emitted by compiler — not handled in `compile_expr`.)
- **`Load`** (`model.py:286`) — Read a variable/field ref. Fields: `ref: ValRef`, `mutable: bool`. Compiled as simple name reference.
- **`Move`** (`model.py:292`) — Move a value out of a ref. Field: `ref: ValRef`. Compiled identically to `Load`.
- **`Store`** (`model.py:297`) — Target of an assignment. Field: `ref: ValRef`. Used as assignment LHS.
- **`Construct`** (`model.py:302`) — Constructor call. Fields: `typ: Type`, `args: Sequence[Expr]`, `kwargs: Mapping[str,Expr]`. Factory: `Construct.make(typ, *args, **kwargs)`.
- **`IsEmpty`** (`model.py:312`) — Check if a collection is empty. Field: `expr: Expr`. Compiled as `len(x) == 0`.
- **`IsInstance`** (`model.py:316`) — Type check. Fields: `expr: Expr`, `typ: Type`. Compiled as `isinstance(x, T)`.
- **`SelfExpr`** (`model.py:323`) — Reference to `self` inside a method. No fields. Compiled as the string `"self"`.
- **`Success`** (`model.py:327`) — Wraps a successful result. Fields: `result_type: Type`, `expr: Expr`. Compiled transparently (just the inner `expr`).
- **`Failure`** (`model.py:332`) — A failed/absent result. Field: `result_type: Type`. Compiled as `None`.
- **`Constant`** (`model.py:338`) — A typed constant. Fields: `typ: Type`, `val: _T`. Compiled via `str(val)`.
- **`TrueBool`, `FalseBool`** (`model.py:344-345`) — Module-level singletons: `Constant(Bool, True)` and `Constant(Bool, False)`.
- **`LiteralString`** (`model.py:348`) — String literal. Field: `value: str`. Compiled via `repr(value)`.
- **`LiteralInt`** (`model.py:353`) — Integer literal. Fields: `typ: Type`, `value: int`. Compiled via `repr(value)`.
- **`LiteralSequence`** (`model.py:358`) — List literal. Field: `values: Sequence[Expr]`. Compiled as `[e1, e2, ...]`.
- **`LiteralMapping`** (`model.py:363`) — Dict literal. Field: `key_values: Sequence[tuple[Expr,Expr]]`. Compiled as `{k: v, ...}`.
- **`LiteralNull`** (`model.py:368`) — Null/None literal. Compiled as `None`.
- **`MemberAccess`** (`model.py:380`) — Base for dot-access. Fields: `member_name: str`, `bound_to: Expr`. Compiled as `obj.member`.
- **`MethodAccess`** (`model.py:386`) — Subclass of `MemberAccess`. Methods: `.call(*args, **kwargs)` → `MethodCall`, `.bind()` → `BoundMethod`.
- **`MethodCall`** (`model.py:395`) — Call to a bound method. Fields: `bound_method: MethodAccess`, `args: Sequence[Expr]`, `kwargs: Mapping[str,Expr]`. Compiled as `obj.method(args)`.
- **`BoundMethod`** (`model.py:402`) — Reference to a method without calling it. Compiled as `obj.method`.
- **`FieldAccess`** (`model.py:413`) — Read/write access to a field. Extends both `MemberAccess` and `ValRef`.
- **`BinOp`** (`model.py:722`) — Binary operation. Fields: `lhs: Expr`, `rhs: Expr`, `op: str`. Compiled as `(lhs) op (rhs)`.
- **`UnaryOp`** (`model.py:728`) — Unary operation. Fields: `operand: Expr`, `op: str`. Compiled as `op(operand)`.
- **`LogicalNegation`** (`model.py:735`) — Boolean NOT. Field: `operand: Expr`. Compiled as `not (operand)`.
- **`LogicalAnd`** (`model.py:740`) — Boolean AND. Extends `BinOp` with default `op="and"`.
- **`LogicalOr`** (`model.py:745`) — Boolean OR. Extends `BinOp` with default `op="or"`.
- **`GreaterThan`** (`model.py:750`) — `>` comparison. Extends `BinOp` with default `op=">"`.
- **`Subtract`** (`model.py:755`) — Subtraction. Extends `BinOp` with default `op="-"`.
- **`Equals`** (`model.py:760`) — Equality comparison. Extends `BinOp` with default `op="=="`.
- **`Subscript`** (`model.py:765`) — Index/subscript access. Fields: `target: Expr`, `index: Expr`. Compiled as `(target[index])`.
- **`LetExpr`** (`model.py:776`) — Walrus-operator binding (`:=`). Fields: `result: Expr`, `var: Var`. Used in `if_` and `while_` conditions; compiled as `(var := result_expr)` in Python output (`py/compiler.py:273,281`).

### Function/Method/Class Declaration Nodes

- **`Function`** (`model.py:428`) — A function. Fields: `name: str|None`, `params: Sequence[Param]`, `return_type: Type`, `block: Block`, `doc: str|None`.
- **`Method`** (`model.py:449`) — Extends `Function` with: `in_class: ClassType`, `mutable_self: bool`, `self_expr: SelfExpr`. Compiled with `self` prepended to params.
- **`Constructor`** (`model.py:639`) — Extends `Method`. Special init: `name=""`, `return_type=Void`, plus `init_list: list[tuple[Field,InitListExpr]]` for field initialization. Compiled into Python `__init__` method.
- **`InitFromParamType`** (`model.py:630`) — Sentinel class. Singleton `INIT_FROM_PARAM` at `model.py:634`. In an init_list pair, means "assign field from the constructor param of the same name" (as opposed to a custom expression).
- **`FieldLookupProxy`** (`model.py:606`) — Builder object; `__getattr__`/`__getitem__` intercept attribute access to return `FieldAccess` nodes. Created by `Expr.fld` and `Expr.mut_fld`.
- **`MethodLookupProxy`** (`model.py:620`) — Builder object; `__getattr__`/`__getitem__` return `MethodAccess` nodes. Created by `Expr.method`.

---

## 2. Type System

### Parameterization

`Type` supports generic type parameters via `params: Mapping[str,ParamType]`. Instantiation produces a new `Type` with `instantiates` pointing to the generic and `arguments` holding the concrete type values (`typemodel.py:85-91`). `Type.root_type()` walks the `instantiates` chain to find the origin generic (`typemodel.py:93-96`). `Type.get_arg` and `get_arg_as_type` look up argument values walking the chain (`typemodel.py:98-120`).

### Global Registry

Every `Type` instance self-registers into `_type_registry: dict[TypeKey, Type]` on construction (`typemodel.py:36,80-83`). The `TypeKey` is frozen and based on `cname`, params, instantiates, and arguments — making types structurally unique by identity.

### Python Backend Type Mapping (`py/reg.py`, `context.py`)

`TypeInfo` (`py/reg.py:20`) maps an IIR `Type` to:
- `module: Module` — import path as tuple of strings; `Builtins = Module(import_path=())` for builtins.
- `name: str` — the annotation-form name (e.g., `"Optional"`, `"Sequence"`).
- `concrete_name: str|None` — the constructor-form name (e.g., `"list"`, `"dict"`).

`import_name(*, concrete=False)` (`py/reg.py:26`) returns dotted import path + name, or the concrete name if `concrete=True` and one exists.

Full mapping registered in `context.py:_register_builtin_types`:

| IIR Type | module | name | concrete_name |
|---|---|---|---|
| `Void` | builtins | `None` | — |
| `UInt64` | builtins | `int` | — |
| `IndexInt` | builtins | `int` | — |
| `SignedIndexInt` | builtins | `int` | — |
| `Bool` | builtins | `bool` | — |
| `String` | builtins | `str` | — |
| `Maybe` | `typing` | `Optional` | — |
| `GenericImmutableSequence` | `typing` | `Sequence` | `list` |
| `GenericMutableHashmap` | `collections.abc` | `MutableMapping` | `dict` |
| `ApplyResultType` | `fltk.fegen.pyrt.memo` | `ApplyResult` | — |
| `Span` | `fltk.fegen.pyrt.terminalsrc` | `Span` | — |
| `MemoEntry` | `fltk.fegen.pyrt.memo` | `MemoEntry` | — |
| `ErrorTracker` | `fltk.fegen.pyrt.errors` | `ErrorTracker` | — |

`GenericMutableSequence` and `GenericImmutableHashmap` are defined in `model.py` but have no registered `TypeInfo`.

---

## 3. Python-Specific Assumptions Baked Into IIR Model

1. **`SelfExpr` / `self` convention** (`model.py:323`, `py/compiler.py:295`): The model has a dedicated `SelfExpr` node that compiles to the string `"self"`. OOP method dispatch is baked in via `Method.self_expr` (`model.py:453`) and `Method.mutable_self` (`model.py:452`). `compile_function` prepends `"self"` to the param list for any `Method` (`compiler.py:175`).

2. **`__init__` naming** (`compiler.py:108`): `Constructor` objects are always compiled as a method named `"__init__"`. The IIR Constructor itself has `name=""` (`model.py:641`), but the Python compiler injects the name.

3. **Walrus operator (`:=`)** (`model.py:776`, `compiler.py:272-281`): `LetExpr` is defined specifically for Python's walrus operator. The compilation explicitly generates `(var := expr)` syntax, which has no equivalent in most other languages.

4. **`isinstance` check** (`model.py:316`, `compiler.py:338-339`): `IsInstance` compiles directly to Python's `isinstance(expr, type)` builtin. The type argument is resolved to a Python constructor string.

5. **`IsEmpty` → `len(...) == 0`** (`compiler.py:334`): The empty-check idiom is Python-specific (`len(x) == 0`). Rust would use `.is_empty()`.

6. **`LiteralNull` / `Failure` → `None`** (`model.py:368-370`, `compiler.py:319,325`): Both null literals and failure results compile to `None`. No notion of `Option<T>` wrapping; `None` is used as both the null value and the failure sentinel.

7. **`Success` transparent** (`compiler.py:321`): `Success(result_type, expr)` compiles as just `expr` — no wrapping. This means success/failure is modeled at the value level (None vs. non-None), not at the type level.

8. **Operator strings are Python syntax** (`model.py:740-760`): `LogicalAnd.op="and"`, `LogicalOr.op="or"` are Python keywords, not `&&`/`||`. `LogicalNegation` compiles to `not (x)` (`compiler.py:341`).

9. **Type annotations as strings** (`compiler.py:49-74`): `iir_type_to_py_annotation` returns Python annotation strings like `"Optional[str]"` or `"typing.Sequence[int]"`. These are Python-specific syntax and module path conventions.

10. **`VarDef` generates `name: type = value` or `name = value`** (`compiler.py:228-234`): Variable declarations emit Python type annotation syntax. `Auto` type suppresses the annotation entirely.

11. **`doc` strings emit triple-quoted Python docstrings** (`compiler.py:82,184`): `klass.doc` and `function.doc` are injected as `"""..."""` Python docstrings.

12. **`base_classes` rendered as positional class arguments** (`compiler.py:80`): `klass.base_classes` are rendered as `class Foo(Base1, Base2):` — Python's multiple-inheritance syntax.

13. **`EnumType` fields are strings only** (`model.py:649`): No values, no backing type. This matches Python's string-valued enum pattern and would need redesign for Rust enums (which can carry data).

14. **`RefType` enum exists but is semantically inert** (`model.py:234-239`): `RefType` has `BORROW`, `MUT_BORROW`, `OWNING`, `SHARED` variants suggestive of Rust ownership, but the Python compiler ignores them entirely — no code path in `py/compiler.py` branches on `ref_type`.

---

## 4. Python Compiler (`py/compiler.py`)

The compiler translates an `iir.Module` into a Python `ast.Module` (Python's stdlib AST). It uses `fltk.pygen` as a helper for constructing AST nodes from source strings (via `ast.parse`).

### Entry Point

`compile(mod: iir.Module, context: CompilerContext) -> ast.Module` (`compiler.py:17`): Iterates `mod.block.body`; dispatches `ClassDef` → `compile_class`, `Function` → `compile_function`. Note: there is a bug at line 25 — `raise NotImplementedError` is reached unconditionally after the two `if` checks (missing `continue`/`return`).

### Class Compilation (`compile_class`, line 77)

1. Creates `ast.ClassDef` via `pygen.klass(name, bases)`.
2. Resolves or synthesizes a `Constructor`.
3. Builds an `iir.Method` named `"__init__"` from the constructor's `init_list` and remaining fields:
   - For each `(field, InitFromParamType)` pair: emits `self.field = param` assignment.
   - For each `(field, expr)` pair: emits `self.field = expr` assignment.
   - For fields not in the init_list: emits `self.field: Type = field.init` as `VarDef` nodes with names prefixed `"self."`.
4. Appends constructor body statements.
5. Compiles each `Method` in the class.

### Function Compilation (`compile_function`, line 172)

Emits `def name(self, p1: T1, p2: T2, ...) -> R:`. Compiles each statement in the block via `compile_stmt`.

### Statement Compilation (`compile_stmt`, line 213)

Dispatches on type:
- `AssignStatement` → `compile_assign` → `target = value` string
- `Return` → `ast.Return`
- `Break` → `ast.Break`
- `VarDef` → `name: Type = init` or `name: Type` or `name = init` (when `Auto`)
- `If` → `compile_if` — emits walrus for `LetExpr` condition
- `WhileLoop` → `compile_while` — emits walrus for `LetExpr` condition
- `ExprStatement` → bare expression statement
- Anything else → `raise NotImplementedError`

`elif` chains (where `orelse` is `iir.If`) raise `NotImplementedError` at `compiler.py:266`.

### Expression Compilation (`compile_expr`, line 294)

Returns a Python source string (not an AST node). Dispatches on type — all handled cases listed in section 1 above. Terminal fallback: `raise AssertionError(repr(expr))` at line 344.

Notable translations:
- `Load | Move` → bare name (ownership semantics erased)
- `Failure` → `"None"`
- `Success` → transparent (no wrapping)
- `LiteralSequence` → `"[e1, e2, ...]"`
- `LiteralMapping` → `"{k: v, ...}"`
- `IsEmpty` → `"(len(x) == 0)"`
- `IsInstance` → `"isinstance(x, T)"`
- `LetExpr` (in `compile_if`/`compile_while`) → `"(var := expr)"`
- `BinOp` → `"(lhs) op (rhs)"` — operator is taken verbatim from `BinOp.op`

### Type Resolution in Compiler

Two functions:
- `iir_type_to_py_annotation(typ, context)` (`compiler.py:49`) — returns annotation string like `"Optional[str]"`. For parameterized types, recursively resolves type arguments.
- `iir_type_to_py_constructor(typ, context)` (`compiler.py:29`) — returns the concrete constructor name like `"list"` or `"dict"`. For `PrimitiveType`, returns `""` (no constructor). For `Maybe`-wrapped types, recursively unwraps.

---

## 5. Context Class

`CompilerContext` (`context.py:43`) is a `@dataclass` with two fields:
- `python_type_registry: TypeRegistry` — default-factory creates empty `TypeRegistry`.
- `capture_trivia: bool = False` — flag for whether trivia (whitespace tokens) should be captured in the CST.

`TypeRegistry` (`context.py:13`) is a `dict[TypeKey, TypeInfo]` wrapper:
- `register_type(type_info)` — allows identical re-registration; raises `ValueError` on conflicting registration.
- `lookup(typ)` — raises `KeyError` if not found.
- `contains(typ)` — boolean check.
- `copy()` — shallow copy (new dict, same `TypeInfo` values).

`create_default_context(*, capture_trivia=False)` (`context.py:50`) creates a `CompilerContext` and registers all built-in and parser-specific type infos via `_register_builtin_types`.

**Purpose**: `CompilerContext` was introduced to eliminate a global type registry that prevented multiple `ParserGenerator` instances from coexisting (tests at `test_context.py:135-201` verify isolation). Each `ParserGenerator` and `CstGenerator` holds its own context.

`get_parser_types()` (`context.py:60`) creates and returns the four parser-specific generic types: `ApplyResultType`, `Span`, `MemoEntry`, `ErrorTracker`. These are also registered in `_register_builtin_types` — so this function is called for its side effect of interning them into the global `_type_registry`.

---

## 6. Python-Specific Idioms Difficult to Express in Rust

1. **`None` as universal null/failure** (`model.py:332,368`, `compiler.py:319,325`): `Failure` and `LiteralNull` both compile to `None`. In Rust, `None` only exists inside `Option<T>`, and there is no universal null. The IIR's `Success`/`Failure` distinction would need to become `Some(T)`/`None` at a structural level, not just a naming convention.

2. **Walrus operator `LetExpr`** (`model.py:776`, `compiler.py:272-281`): Python-specific `:=` syntax is a first-class IIR node. Rust has `if let` and `while let` pattern syntax which is semantically similar but syntactically incompatible.

3. **`isinstance` dynamic dispatch** (`model.py:316`, `compiler.py:338`): `IsInstance` maps directly to Python's runtime type introspection. In Rust this would require trait objects, enum matching, or `Any::downcast_ref`.

4. **`IsEmpty` → `len()` call** (`compiler.py:334`): Python's `len()` protocol. Rust uses `.is_empty()` on trait-specific types; no unified length protocol.

5. **`BinOp.op` as raw Python keyword strings** (`model.py:740-745`): `"and"`, `"or"` are Python keywords directly embedded in the IIR. No abstraction separates the operator representation from the target language.

6. **`UnaryOp` compiled as `op(operand)`** (`compiler.py:303`): The format `op(operand)` (e.g., `not(x)`) is Python function-call syntax being used for operators. This is accidental — `not` is actually a keyword in Python and `not(x)` works as a statement, but it conflates operators and function calls.

7. **Multiple inheritance** (`model.py:467`, `compiler.py:80`): `ClassType.base_classes` is a `Sequence[Type]` and is compiled as Python multiple inheritance. Rust has no multiple inheritance (only single trait implementation per trait per type).

8. **String-keyed kwargs throughout** (`model.py:305,399`, `compiler.py:287-291`): `Construct`, `MethodCall` all carry `kwargs: Mapping[str, Expr]`, which maps to Python's `**kwargs` keyword argument syntax. Rust functions do not have keyword arguments.

9. **`RefType` is decorative** (`model.py:234-239`): Rust-style ownership semantics (`BORROW`, `MUT_BORROW`, `OWNING`, `SHARED`) are present in the model but not enforced or emitted — they are placeholders that a Rust backend would need to make real.

10. **`EnumType` as stringly-typed variant names** (`model.py:645-676`): IIR enums are just lists of strings with no payloads. Python's `enum.Enum` works this way. Rust enums carry data and have distinct types per variant; the IIR model would need extension.

11. **`doc: str|None` in `Function`, `ClassType`** (`model.py:433,466`): Docstrings are first-class in the model, mapping to Python docstring convention. Rust has doc comments (`///`), not docstrings.

12. **Global `_type_registry`** (`typemodel.py:36`): All `Type` instances self-register into a module-level global dict. This creates a process-global side-effect on type construction with no cleanup mechanism — an anti-pattern for concurrent use or testing without isolation.
