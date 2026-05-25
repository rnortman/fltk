# Alternative IR Analysis for Multi-Language Parser/Unparser Generation

Concise. Precise. Token-dense. Every claim anchored to source code.

---

## 1. Current Architecture: Three Distinct Representations

FLTK currently uses three representations, each serving a different purpose, and no single one of them is a suitable universal codegen IR.

### 1.1 GSM (Grammar Semantic Model) -- the grammar description

**File:** `fltk/fegen/gsm.py`

The GSM is a declarative description of the grammar itself. Key types: `Grammar` (rules + identifiers, gsm.py:19-22), `Rule` (name + alternatives, gsm.py:25-51), `Items` (sequence of items with separators, gsm.py:70-98), `Item` (label + disposition + term + quantifier, gsm.py:101-111), `Separator` (NO_WS / WS_ALLOWED / WS_REQUIRED, gsm.py:54-67), `Disposition` (SUPPRESS / INCLUDE / INLINE, gsm.py:176-179), `Quantifier` (Required / NotRequired / OneOrMore / ZeroOrMore, gsm.py:188-246), and `Term` (union of Identifier / Literal / Regex / Sequence[Items] / Invocation, gsm.py:157-163).

The GSM says *what* to parse, not *how* to parse. Both `gsm2parser.py` and `gsm2unparser.py` read GSM and produce IIR. `gsm2tree.py` reads GSM and produces Python AST directly via `pygen`. The GSM is language-neutral by nature.

### 1.2 IIR (Imperative Intermediate Representation) -- the codegen IR

**Files:** `fltk/iir/model.py` (780 lines), `fltk/iir/typemodel.py` (124 lines)

The IIR is an imperative, OOP-flavored AST. It has classes, methods, fields, scopes, blocks, statements (If, WhileLoop, Return, Break, VarDef, AssignStatement, ExprStatement), and expressions (Load, Store, Move, Construct, MethodCall, BinOp, IsInstance, LetExpr, etc.).

It is used by:
- `gsm2parser.py` -- builds an entire `iir.ClassType` with methods, blocks, and expressions (gsm2parser.py:42-46, 100-188, 341-407, 439-756)
- `gsm2unparser.py` -- builds an `iir.ClassType` similarly (gsm2unparser.py:52, 200-1519)
- `iir/py/compiler.py` -- compiles IIR to Python `ast` nodes (compiler.py:77-344)

It is **not** used by:
- `gsm2tree.py` -- which builds Python AST directly via `pygen`, only using `iir.Type.make()` for type identity/registry (gsm2tree.py:69-78, 95-244)

### 1.3 Python AST + pygen -- direct Python emission

**Files:** `fltk/pygen.py` (124 lines), `fltk/fegen/gsm2tree.py`

`pygen.py` is a convenience factory over Python's `ast` module. `gsm2tree.py` uses it to emit CST node classes directly as Python AST, bypassing the IIR entirely.

### Asymmetry summary

| Generator | Input | Representation used | Output path |
|---|---|---|---|
| `gsm2parser.py` | GSM | IIR (full) | IIR -> py/compiler -> ast -> source |
| `gsm2unparser.py` | GSM | IIR (full) | IIR -> py/compiler -> ast -> source |
| `gsm2tree.py` | GSM | pygen directly | pygen -> ast -> source |

This asymmetry (gsm2tree bypasses IIR) is the first structural issue any multi-language IR must solve.

---

## 2. What the GSM Already Is, and What It Lacks as an IR

The GSM is already a language-neutral declarative grammar description. From it alone, you can mechanically derive:

**Parser behavior** (currently done by `gsm2parser.py`): recursive descent with packrat memoization, trivia handling (WS_ALLOWED/WS_REQUIRED separators), left-recursion via seed growing.

**CST shape** (currently done by `gsm2tree.py`): one class per rule, with a `children: list[tuple[Label|None, ChildUnion]]` field, typed label-based accessors, span tracking.

**Unparser behavior** (currently done by `gsm2unparser.py`): walk CST children by position, emit text for literals, extract span text for regexes, recurse for identifiers, thread accumulator for Doc combinator building, handle trivia preservation.

What the GSM **lacks** for being a complete codegen IR:

1. **No runtime semantics.** It doesn't say how memoization works, how left recursion is resolved, or how errors are tracked. These are in `fltk/fegen/pyrt/memo.py` (Packrat, seed-growing algorithm, lines 77-257), `fltk/fegen/pyrt/errors.py` (ErrorTracker), and `fltk/fegen/pyrt/terminalsrc.py` (TerminalSource). A codegen target must know which runtime to call.

2. **No formatting/unparse config.** Formatting operations (group, nest, join, before/after/separator specs) come from `FormatterConfig` (`fltk/unparse/fmt_config.py:134`), not the GSM. The unparser generator fuses GSM + FormatterConfig to produce IIR.

3. **No CST representation description.** The CST shape is derived from the GSM but involves decisions about type unions, label enums, and accessor method generation (gsm2tree.py:109-244) that aren't in the GSM.

4. **`Invocation` and `Expression` are unimplemented.** `gsm.Invocation` (gsm.py:249-256) and `gsm.Expression` (gsm.py:259) exist in the GSM data model but `_gen_consume_term_expr` raises `NotImplementedError` for them (gsm2parser.py:308-309), as does `model_for_item` in gsm2tree.py:246-257.

---

## 3. Python-Specificity in the Current IIR

The IIR is heavily Python-flavored. A Rust backend cannot reuse it as-is. Verified facts:

| IIR Feature | Code location | Python-specific aspect |
|---|---|---|
| `LetExpr` (walrus `:=`) | model.py:776, compiler.py:272-281 | Python-specific syntax; Rust has `if let` |
| `LogicalAnd.op="and"`, `LogicalOr.op="or"` | model.py:740-745 | Python keywords; Rust uses `&&`/`\|\|` |
| `LogicalNegation` -> `not (x)` | compiler.py:341 | Python keyword; Rust uses `!` |
| `IsEmpty` -> `len(x) == 0` | compiler.py:334 | Python `len()` protocol; Rust: `.is_empty()` |
| `IsInstance` -> `isinstance(x, T)` | compiler.py:338-339 | Dynamic type check; Rust: `matches!` or enum |
| `Success` -> transparent | compiler.py:321 | No wrapping; Rust needs `Some(T)` |
| `Failure` -> `None` | compiler.py:319 | Python None; Rust: `None` in `Option<T>` |
| `SelfExpr` -> `"self"` | model.py:323, compiler.py:296 | Python method convention |
| Constructor -> `__init__` | compiler.py:108 | Python dunder method |
| `kwargs: Mapping[str, Expr]` | model.py:305,399 | Python keyword args; Rust has none |
| `EnumType` as string list | model.py:645-676 | No payload; Rust enums carry data |
| `RefType` (BORROW/OWNING/etc) | model.py:234-239 | Present but semantically inert (compiler ignores) |
| `BinOp.op` as raw strings | model.py:722-760 | Operator strings are Python syntax |
| Type annotations as Python strings | compiler.py:49-74 | `"Optional[str]"` etc. |

The `RefType` enum (model.py:234-239) has Rust-like variants (BORROW, MUT_BORROW, OWNING, SHARED) but the Python compiler never branches on them (confirmed: no `ref_type` check anywhere in compiler.py). This was forward-looking infrastructure that was never activated.

---

## 4. Candidate IR Approaches

### 4.1 Enhanced GSM as the Sole IR (Declarative Approach)

**Concept:** Elevate the GSM to a complete declarative specification. Each language backend interprets the GSM directly, making language-specific decisions during interpretation.

**What this means concretely:**
- The GSM already specifies all information needed for parser, CST, and unparser generation
- Each backend (Python, Rust) would have its own `gsm2parser_py.py`, `gsm2parser_rs.py` etc.
- No shared imperative IR at all; the GSM *is* the IR

**What exists that supports this:**
- `gsm2parser.py` already reads GSM and makes all decisions about memoization structure, packrat apply patterns, trivia handling (lines 27-756)
- `gsm2tree.py` already reads GSM and makes all CST class shape decisions (lines 33-303)
- `gsm2unparser.py` already reads GSM + FormatterConfig (lines 30-1549)
- The GSM data structures are frozen dataclasses, hashable, serializable (gsm.py: all `@dataclass(frozen=True, slots=True)`)
- ANTLR uses this exact approach: grammar AST as shared IR, per-language code generation template engines

**What would need to change:**
- No IIR at all -- each backend generates target-language code directly from GSM
- Each backend duplicates the structural logic currently in `gsm2parser.py` (756 lines) and `gsm2unparser.py` (1549 lines)
- Formatter config integration would be per-backend

**Key trade-off:** Duplicates ~2300 lines of generation logic per target language. The GSM tells you "rule R has alternatives A1, A2 with separator WS_ALLOWED" but not "generate method `parse_R__alt0__item0` that calls `apply__parse_R`" -- that mapping is what the generators do. However, ~60% of the code in gsm2parser.py and gsm2unparser.py is IIR node construction; the pure structural decisions (method decomposition, control flow patterns) are a smaller fraction.

### 4.2 Two-Layer IR: Declarative Grammar Model + Language-Neutral Imperative IR

**Concept:** Keep the GSM as the top-level declarative description. Introduce a new language-neutral imperative IR that replaces the current Python-flavored IIR.

**What the new IR would need:**
- Same statement/expression vocabulary as current IIR but without Python-specific nodes
- Abstract operator representation (enum, not string `"and"/"or"`)
- Proper Option/Result type semantics (not `None`-as-failure)
- No kwargs, no walrus operator, no `isinstance`
- Pattern matching / enum variant dispatch instead of `isinstance`
- `self` as an abstract receiver concept, not a literal string

**Verified nodes that would survive unchanged:** `Block`, `If`, `WhileLoop`, `Return`, `Break` (model.py:110-709); `VarDef`, `AssignStatement`, `ExprStatement` (model.py:274, 697, 712); `Load`, `Store`, `Move` (model.py:286-298); `Construct`, `FieldAccess`, `MethodCall` (model.py:302, 413, 395); `LiteralString`, `LiteralInt`, `LiteralSequence`, `LiteralMapping` (model.py:348-366); `BinOp` structure (but with abstract op enum, not string); `Subscript` (model.py:765); `ClassType`, `Method`, `Function`, `Field`, `Param` (model.py:428-598).

**Nodes needing redesign:** `LetExpr` -> abstract conditional binding; `IsInstance` -> abstract type dispatch; `IsEmpty` -> abstract collection empty check; `Success`/`Failure` -> abstract Result/Option; `LogicalAnd`/`LogicalOr`/`LogicalNegation` -> abstract boolean ops with enum-based op; `SelfExpr` -> abstract receiver; `EnumType` -> needs variant payloads for Rust.

**Key trade-off:** Significant refactoring of `gsm2parser.py` and `gsm2unparser.py` to emit the new IR, plus two compiler backends. But the ~2300 lines of structural generation logic remain shared.

### 4.3 Declarative Parser/Unparser Description (Domain-Specific IR)

**Concept:** An IR between GSM and imperative code that describes parser/unparser *behavior* declaratively without prescribing imperative structure.

A "parser description" IR would capture: "Rule R: try alternatives A1, A2 in order; memoize with packrat." "Alternative A1: parse items [I1, I2, I3] sequentially; trivia between I1-I2; fail if I2 misses." "Item I1: consume literal ':=', suppress from CST."

**What exists that partially does this:**
- `gsm2parser.ParserFn` (gsm2parser.py:18-25): name, apply_name, cache_name, result_type, rule_id, inline_to_parent
- `gsm2parser.ConsumeTermInfo` (gsm2parser.py:231-235): expr, result_type, inline_to_parent
- `gsm2unparser.UnparserFn` (gsm2unparser.py:33-36): name, result_type
- `gsm2tree.ItemsModel` (gsm2tree.py:22-30): labels mapping, types set

These are metadata about the generated code, not a full description. To make this a real IR, you'd need to formalize the method decomposition, control flow patterns, and data threading. Essentially a mini-language for describing recursive-descent parsers.

**Key trade-off:** Cleanest separation of concerns, but it's a new abstraction layer that doesn't exist. The domain-specific IR is complex to design correctly (must cover left recursion, trivia recursion guards, inline-to-parent, formatter anchor operations).

### 4.4 Off-the-Shelf IRs

**LLVM IR / Cranelift IR:** Too low-level. FLTK needs to emit human-readable source code in target languages, not machine code.

**MLIR:** Designed for compiler dialects, oriented toward numeric/tensor computation. Could theoretically host a "parser dialect" but massive overkill and wrong abstraction level.

**Tree-sitter's grammar.js:** Declarative grammar format similar to GSM, but its codegen is C-only and tightly coupled. Not reusable.

**ANTLR's internal model:** Closest to approach 4.1. Each ANTLR target has its own code generation template engine. The grammar model is the shared IR.

**Protocol Buffers / FlatBuffers schema:** Serialization IRs. Could serialize the GSM for cross-language tool use but don't help with codegen.

### 4.5 Hybrid: GSM + Codegen Plan + Thin Backend

A pragmatic middle ground: keep the GSM as the declarative IR, extract the method decomposition metadata into a shared "codegen plan" structure, and let each backend compile the plan.

What this looks like concretely:
- `ItemsModel` (gsm2tree.py:22-30) already captures CST shape -- share it
- `ParserFn` (gsm2parser.py:18-25) already captures parser method structure -- share it
- `UnparserFn` (gsm2unparser.py:33-36) captures unparser method structure -- extend it
- A "codegen plan" would be: list of `ParserFn` entries, each with pre-computed structural decisions (what terms to consume, what separators to handle, what quantifier logic to use)
- Each backend renders the plan to source code, but the plan computation happens once

---

## 5. What the Generators Actually Compute (Shared Logic Analysis)

### 5.1 Parser generation shared logic (gsm2parser.py)

Target-language-independent decisions:

1. **Method decomposition:** Rules -> `parse_{rule}` + `apply__parse_{rule}`. Alternatives -> `parse_{rule}__alt{N}`. Items -> `parse_{rule}__alt{N}__item{M}`. Sub-expressions -> `...__alts`. (gsm2parser.py:317-328, 616-651, 653-756, 409-535)

2. **Memoization wiring:** Each memoized rule gets cache field, apply wrapper calling `packrat.apply(rule_callable, rule_id, rule_cache, pos)`, and rule_id. (gsm2parser.py:341-407)

3. **Separator handling:** NO_WS -> no-op; WS_ALLOWED -> optional trivia parse; WS_REQUIRED -> required trivia parse with failure return. Trivia rules use raw `\s+` regex to avoid recursion. (gsm2parser.py:537-614)

4. **Item quantifier logic:** Required -> fail on miss. Optional -> no-op on miss. OneOrMore -> while loop + fail if zero matches. ZeroOrMore -> while loop. (gsm2parser.py:409-535, 691-728)

5. **Inline handling:** `inline_to_parent` flag: when true, `children.extend(...)` instead of `append_label(...)`. (gsm2parser.py:495-509, 713-716)

6. **Trivia capture flag:** `context.capture_trivia` controls whether trivia nodes are appended. (gsm2parser.py:584-590, 605-611)

### 5.2 Unparser generation shared logic (gsm2unparser.py)

1. **Method decomposition:** Same pattern as parser. (gsm2unparser.py:192-254, 701-770, 1256-1362, 440-463)

2. **Accumulator threading:** Every method takes and returns `(accumulator, pos)`. (gsm2unparser.py:669-699)

3. **Trivia processing:** Check bounds, check if child is Trivia, check preservability, call trivia unparser, wrap in SeparatorSpec. (gsm2unparser.py:929-1122)

4. **Formatter config integration:** Anchor operations (group/nest/join push/pop) before/after items. (gsm2unparser.py:1167-1254)

5. **Suppressed item handling:** Literals regenerated from grammar, regexes/identifiers raise errors. (gsm2unparser.py:465-511)

6. **Position advancement:** INCLUDE items advance pos by 1; SUPPRESS items don't. (gsm2unparser.py:1434-1442, 1475-1481)

### 5.3 CST generation shared logic (gsm2tree.py)

1. **Model computation:** Iterate items, fold in inline rules, track labels-to-types mapping. (gsm2tree.py:259-303)

2. **Class shape:** One class per rule, `Label` enum, `span` field, `children` field, five methods per label. (gsm2tree.py:109-244)

3. **Type union computation:** All possible child types across alternatives. (gsm2tree.py:85-93)

4. **Trivia type injection:** If rule has WS separators, add Span (trivia rules) or _trivia rule type (non-trivia rules). (gsm2tree.py:296-301)

---

## 6. Structural Constraints on IR Choice

### 6.1 The CST shape must be identical across languages

For PyO3 wrapping, the Rust CST must present the same Python interface: same class names, same `children_foo()` / `child_foo()` / `maybe_foo()` methods, same `Label` enum members, same `span` field, same `children` list structure. The `ItemsModel` (gsm2tree.py:22-30) captures this target-neutrally.

### 6.2 The parser runtime must exist in the target language

The generated parser calls `Packrat.apply()` (memo.py:82-156), `TerminalSource.consume_literal/consume_regex` (terminalsrc.py:31-43), `ErrorTracker.fail_literal/fail_regex` (errors.py:29-40). These must be implemented natively in the target language.

### 6.3 The unparser runtime must exist in the target language

The generated unparser uses `DocAccumulator` (accumulator.py:18), `UnparseResult` (pyrt.py:15), `extract_span_text` (pyrt.py:33), and the full Doc combinator type hierarchy (combinators.py:9-253). `Renderer` (renderer.py:41) and `resolve_spacing_specs` (resolve_specs.py:30) are called after generation, not during.

### 6.4 The formatter config is target-neutral

`FormatterConfig` (fmt_config.py:134) is pure data parsed from `.fltkfmt` files. Contains spacing values (Doc instances), anchor configs, operation types. Shareable across backends.

---

## 7. What Information Each Backend Actually Needs

Verified by reading every codegen path.

### Parser backend needs:
- Rule name, alternatives, items (from GSM)
- Method decomposition: names, memoization flag, result types (computed by gsm2parser.py:314-328)
- For each item: term type (Identifier/Literal/Regex/Sequence), label, disposition, quantifier (from GSM)
- Separator handling: which separator before/after each item (from GSM)
- Trivia rule identity and recursion guard rule (from GSM classify_trivia_rules, gsm.py:273-301)
- Whether to capture trivia (from CompilerContext.capture_trivia)
- CST node types per rule (from CstGenerator.iir_type_for_rule, gsm2tree.py:69-78)
- Runtime type references: ApplyResult, Span, MemoEntry, ErrorTracker, Packrat, TerminalSource

### CST backend needs:
- Rule name -> class name mapping (gsm2tree.py:46-47: PascalCase conversion)
- Per-rule ItemsModel: labels -> types, all types (gsm2tree.py:22-30)
- Span type as a child type for terminals
- Trivia type injection (gsm2tree.py:296-301)

### Unparser backend needs:
- Everything the parser backend needs, plus:
- FormatterConfig: spacing defaults, anchor configs, trivia config (fmt_config.py:134)
- CST node type names for isinstance checks (gsm2unparser.py:164-176)
- Doc combinator type references (gsm2unparser.py:72-162)

---

## 8. Open Factual Questions

1. **RefType activation plan.** `RefType` (model.py:234-239) has Rust-like variants but the Python compiler ignores them. No code path in `py/compiler.py` branches on `ref_type`.

2. **Invocation/Expression coverage.** `gsm.Invocation` and `gsm.Expression` exist (gsm.py:249-259) but are unimplemented in both parser and CST generators. The `fltk.fltkg` grammar uses them (lines 29-35) but `fegen.fltkg` does not.

3. **gsm2tree IIR bypass.** `gsm2tree.py` does not use IIR for code structure, only for type identity (gsm2tree.py:69-78). If a new IR subsumes the IIR, `gsm2tree` must be ported or continue bypassing.

4. **Global _type_registry cleanup.** Every `Type` instance self-registers into `_type_registry: dict[TypeKey, Type]` (typemodel.py:36, 80-83). The duplicate-registration check is commented out (typemodel.py:80-82: `pass` instead of raise). This global mutable state would complicate multi-backend scenarios.

5. **ast.unparse round-trip in unparser generation.** `plumbing.py:272` does `exec(ast.unparse(module), exec_globals)` while `plumbing.py:105,129` for parser generation does `exec(compile(module_ast, ...))`. Inconsistent paths.
