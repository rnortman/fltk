# Exploration: Can a rule named `_` or `__` reach the code generators?

Concise. Precise. No fluff. Audience: smart LLM/human reviewing the `empty-cn-underscore-rule` TODO.

## Question

Is there post-grammar-parsing validation that rejects a rule named `_` or `__` before it reaches the Python or Rust CST/parser code generators?

## Pipeline stages

### 1. Grammar-level regex (`fegen.fltkg:16`)

```
identifier := name:/[_a-z][_a-z0-9]*/ ;
```

`_` and `__` both match. The lexer admits them at parse time.

### 2. `fltk2gsm.Cst2Gsm.visit_rule` (`fltk/fegen/fltk2gsm.py:18-22`)

Extracts the rule name as a bare string from the span. No name validation. A rule named `_` becomes `gsm.Rule(name='_', ...)`.

### 3. `gsm.classify_trivia_rules` (`fltk/fegen/gsm.py:289-317`)

Classifies rules reachable from `_trivia` as trivia rules. A rule named `_` is **not** `_trivia`, so it is not classified as a trivia rule — it passes through as a normal non-trivia rule.

### 4. `gsm.validate_*` functions (`fltk/fegen/gsm.py:344-419`)

Three validators run inside `classify_trivia_rules`: `validate_trivia_rule_not_nil`, `validate_no_repeated_nil_items`, `validate_trivia_separation`. None inspects rule names. All pass for a rule named `_`.

### 5. `gsm2tree.CstGenerator.__init__` (`fltk/fegen/gsm2tree.py:33-44`)

Calls `model_for_rule` for every rule. No name validation. Succeeds for `_`.

**Key behavior**: the model for `_ := /[a-z]+/` (no label, regex term) has `types=set()` and `labels={}` because the item's disposition is `SUPPRESS` (no explicit label + non-Sequence term → `gsm2tree.py:119-121`). The model for `_ := val:/[a-z]+/` (explicit label) has `types={Span.key}` and `labels={'val': ...}` — non-empty.

### 6. `naming.snake_to_upper_camel('_')` (`fltk/fegen/naming.py:22`)

```python
return "".join(part.capitalize() for part in name.lower().split("_"))
```

`'_'.split('_')` → `['', '']`. `''.capitalize()` → `''`. Result: `''` (empty string).  
`'__'.split('_')` → `['', '', '']` → `''` (also empty).  
`'_foo'.split('_')` → `['', 'foo']` → `'Foo'` (loses the leading underscore, but is non-empty).

**All underscore-only names collapse to the empty string CN.**

---

## Python backend — what happens at generation time

### `gsm2tree.CstGenerator.gen_py_module` (`gsm2tree.py:171-227`)

Calls `self._node_kind_enum()` at line 205, which calls `self.node_kind_member_name(rule.name)` (line 138). For `_`, `node_kind_member_name` returns `''.upper()` = `''`. Then at line 139:

```python
node_kind.body.append(pygen.stmt(f"{member} = enum.auto()"))
# member = '' → stmt_py = ' = enum.auto()'
```

`pygen.stmt` calls `ast.parse(' = enum.auto()')` (`pygen.py:50`), which raises:

```
IndentationError: unexpected indent (<unknown>, line 1)
```

**Empirically confirmed**: `generate` → `_node_kind_enum` → `pygen.stmt` crashes at `pygen.py:50` for any rule whose `node_kind_member_name` is `''`.

This occurs before `py_class_for_model` is called, so the empty-model guard at `gsm2tree.py:252-256` is never reached for this path. For the no-label case (`types=set()`), `model_for_rule` at `gsm2tree.py:1009-1026` would also skip model building for suppressed-only rules — but `gen_py_module` crashes first.

### `gsm2parser.ParserGenerator.__init__` (`gsm2parser.py:86-244`)

No rule-name validation. Constructs a `ParserGenerator` successfully for `_ := val:/[a-z]+/`. The parser method names include `apply__parse__` (empty segment for `_`), which is syntactically valid Python (double underscore). If `gen_py_module` had not crashed, the parser would be generated with method name `apply__parse__` — a dunder-style name but not inherently a Python error.

---

## Rust backend — what happens at generation time

### `gsm2tree_rs.RustCstGenerator.__init__` (`gsm2tree_rs.py:82-164`)

Validation at lines 96-121:

```python
if not _IDENTIFIER_RE.match(rule.name):
    raise ValueError(...)
```

`_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")` (line 22). Both `_` and `__` match this pattern. **No rejection.**

```python
class_name = self._py_gen.class_name_for_rule_node(rule.name)
if class_name in _RESERVED_CLASS_NAMES:
    raise ValueError(...)
```

For `_`, `class_name = ''`. The empty string is **not** in `_RESERVED_CLASS_NAMES` (which contains `'NodeKind'`, `'Span'`, etc.). **No rejection.**

Cross-rule collision check at lines 141-164 also does not catch `''`; no other rule would have CN `''` unless the grammar has two underscore-only rules, in which case the collision check would raise for the duplicate CN claim.

**Empirically confirmed**: `RustCstGenerator.__init__` succeeds for both `_ := /[a-z]+/` and `_ := val:/[a-z]+/`.

### `gsm2tree_rs.RustCstGenerator.generate` (`gsm2tree_rs.py:344-370`)

Calls `self._rule_info()` at line 351, which calls `self._py_gen.rule_models[rule.name]` (line 175). For `_ := /[a-z]+/` (suppressed item, `types=set()`), line 182 raises:

```
RuntimeError: Model class `` would have no members; ensure there is at least one term included in the model.
```

For `_ := val:/[a-z]+/` (explicit label, non-empty model), `_rule_info` succeeds and `generate()` proceeds to emit malformed Rust:

- `NodeKind` enum emits `#[pyo3(name = "")] ,` (empty variant name — Rust syntax error).
- Node struct emits `pub struct  {` (empty struct name — Rust syntax error).
- All Rust identifiers derived from CN `''` are empty: `pub struct `, `pub enum Child`, `pub enum Label`, `pub struct Py`, etc.

**Empirically confirmed**: `generate()` for `_ := val:/[a-z]+/` completes (returns a string) without raising. The generated code is not valid Rust.

### `gsm2parser_rs.RustParserGenerator.__init__` (`gsm2parser_rs.py:80-134`)

Delegates to `RustCstGenerator.__init__` (so same behavior). No additional name validation. For `_ := val:/[a-z]+/`, init succeeds and `generate()` emits Rust with method names `apply__parse__` and `parse__` (double-underscored), which are syntactically valid Rust function names.

---

## Entry points summary

| Entry point | File | Behavior for rule `_` |
|---|---|---|
| `plumbing.parse_grammar` | `fltk/plumbing.py:120` | **Succeeds**; returns `gsm.Grammar` with `Rule(name='_')` |
| `plumbing.generate_parser` | `fltk/plumbing.py:212` | **Crashes** at `gsm2tree.gen_py_module` → `IndentationError` |
| `genparser generate` (CLI) | `fltk/fegen/genparser.py:120` | **Crashes** at `gen_py_module` → `IndentationError` (unhandled, typer prints traceback) |
| `genparser gen-rust-cst` (CLI) | `fltk/fegen/genparser.py:265` | `RustCstGenerator.__init__` succeeds (no error); `generate()` raises `RuntimeError` for suppressed-only rule; for INCLUDE rule, `generate()` returns silently-malformed Rust |
| `genparser gen-rust-parser` (CLI) | `fltk/fegen/genparser.py:368` | Same path as above through `RustCstGenerator.__init__` |

---

## Underscore-prefix rules (`_foo`)

`snake_to_upper_camel('_foo')` = `'Foo'` (non-empty). These do **not** trigger the empty-CN bug. Rules like `_trivia` are intentionally underscore-prefixed and work correctly.

---

## Key facts / open gaps

1. **No validation at or before the GSM layer rejects `_` or `__` as rule names.** The grammar regex, `fltk2gsm`, and all `gsm.validate_*` functions are silent.

2. **Python backend**: crashes unconditionally at `gsm2tree.py:139` → `pygen.py:50` with `IndentationError` for any rule whose CN is `''`, regardless of whether the rule has included terms or not. This is the first point of failure and occurs before the `types=set()` guard at `gsm2tree.py:252`.

3. **Rust backend**: `RustCstGenerator.__init__` silently passes for `_`/`__` (both `_IDENTIFIER_RE` and the reserved-name check miss CN `''`). `generate()` raises `RuntimeError` for suppressed-only rules (caught by `genparser gen-rust-cst`), but **for INCLUDE rules returns malformed Rust without error or warning**. The TODO comment at `gsm2tree_rs.py:18-21` documents this exactly.

4. **`gsm2parser_rs.RustParserGenerator`**: no rule-name validation beyond what `RustCstGenerator.__init__` provides. Would generate Rust parser code referencing `cst::` (empty module path segment) which is a Rust syntax error.

5. **`TODO(empty-cn-underscore-rule)`** at `gsm2tree_rs.py:18-21` already names both the `_IDENTIFIER_RE` admission and the missing generation-time diagnostic as the bug, and proposes two fixes (reject empty CN, or tighten the regex to require `[a-z0-9]`). The exploration confirms both fixes are appropriate for the Rust backend; the Python backend needs the same guard (or shares it if validation is lifted into the GSM layer).
