# Items Child-Value Union Investigation

Base commit: a5cffc5. Concise, no fluff; audience is an informed LLM/human reviewer.

---

## 1. Exact Static Type of `Items.children` Value Members

**Generated CST** (`fltk/fegen/fltk_cst.py:182–184`):
```python
children: list[tuple[Label | None, typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]]
```

**Generator source** (`gsm2tree.py`):

The child-value union is built by `model_for_rule` (line 457) composing `ItemsModel.types` from three sources:

1. **`"item"` → `Item`**: `model_for_item` (line 253) returns `ItemsModel(types={item.term.value})` when the term is an `Identifier`. The `items` grammar rule has `item` as its only non-separator, non-sub-expression item → `Item` enters the union.

2. **`"_trivia"` → `Trivia`**: `model_for_rule` (lines 457–462) checks `rule_has_whitespace_separators`. The `items` rule uses `,` (WS_ALLOWED) separators between its sub-expressions → `rule_has_whitespace_separators` returns True. Since `items` is **not** a trivia rule, it incorporates `ItemsModel(types={"_trivia"})` → `"_trivia"` maps to class name `Trivia` → `Trivia` enters the union.

3. **`Span.key`** (literal/separator): `model_for_item` (line 254) returns `ItemsModel(types={self.Span.key})` for `gsm.Literal | gsm.Regex` terms. The `items` grammar rule contains `( no_ws:"." | ws_allowed:"," | ws_required:":" )?` — these are labeled literals whose terms are `Literal`. Their `ItemsModel` contributes `Span.key`, and the labels `no_ws`, `ws_allowed`, `ws_required` are registered in `model.labels` (line 274–276). `Span.key` thus enters both `model.types` (broadening the union) and per-label type sets.

**Union members and their origin:**

| Member | Source in grammar | Source in generator |
|---|---|---|
| `Item` | `item` identifier reference | `model_for_item` returning rule name key; `iir_type_for_rule("item")` |
| `Trivia` | whitespace separator between sub-expressions | `model_for_rule` adding `"_trivia"` when `rule_has_whitespace_separators` is True |
| `fltk.fegen.pyrt.terminalsrc.Span` | labeled literals `"."`, `","`, `":"` | `model_for_item` returning `Span.key` for `gsm.Literal` terms |

---

## 2. Span: What It Is and Why It Is a Child Value

`Span` (`fltk.fegen.pyrt.terminalsrc.Span`) is the representation of **matched literal/terminal text** — it carries `start` and `end` byte offsets into the source.

In the `items` rule (`fegen.fltkg:5–10`):
```
items :=
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  item ,
  ( ( no_ws:"." | ws_allowed:"," | ws_required:":" ) , item , )* ,
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  ;
```

The `.`, `,`, `:` literals are **the separator punctuation tokens themselves** (the grammar representation of NO_WS/WS_ALLOWED/WS_REQUIRED separators), each given an explicit label (`no_ws:`, `ws_allowed:`, `ws_required:`). Because they are labeled, they are not suppressed. Each literal term → `model_for_item` returns `Span.key` → `append_no_ws(child: Span)` / `append_ws_allowed(child: Span)` / `append_ws_required(child: Span)` typed methods are generated.

**Evidence from generated parser** (`fltk_parser.py:342, 361, 380`):
```python
result.append_no_ws(child=item0.result)   # item0 returned by consume_literal(pos, ".")
result.append_ws_allowed(child=item0.result)  # consume_literal(pos, ",")
result.append_ws_required(child=item0.result)  # consume_literal(pos, ":")
```

So `Span` children with labels `NO_WS`/`WS_ALLOWED`/`WS_REQUIRED` represent the **separator punctuation characters** (`.`, `,`, `:`) parsed out of the grammar source text. This is **intended design**: the grammar tokens for separators are first-class CST nodes labeled by separator kind.

These are distinct from the **trivia-capture path**. In `_gen_separator_handling` (`gsm2parser.py:584–610`), when `capture_trivia=True`, the parsed whitespace/trivia span is appended with `label=None`. For the committed fegen parser `capture_trivia=False`, so no unlabeled trivia `Span` children are appended at runtime — only the labeled separator-literal `Span` children from the grammar rule itself.

---

## 3. Trivia: Is It Spuriously in the Static Union?

**Short answer: yes, it is spuriously in the static type when `capture_trivia=False`.**

**Why it is still present:** `gsm2tree.CstGenerator` builds the `ItemsModel` from the grammar structure alone, with no reference to `context.capture_trivia` (`gsm2tree.py:457–462`):
```python
if self.rule_has_whitespace_separators(rule):
    if rule.is_trivia_rule:
        model.incorporate(ItemsModel(types={self.Span.key}))
    else:
        model.incorporate(ItemsModel(types={"_trivia"}))
```

The tree generator runs the same logic regardless of `capture_trivia`. The `Trivia` type enters the union because the `items` grammar rule has WS_ALLOWED separators, not because trivia will actually be appended at runtime.

**The parser codegen does condition on `capture_trivia`** (`gsm2parser.py:584, 605`):
```python
if self.context.capture_trivia:
    sep_if.block.expr_stmt(result_var.method.append.call(child=sep_ws_var.fld.result.move(), label=...))
```

So when `capture_trivia=False` (the committed fegen parser), no `Trivia` node is ever appended to `Items.children` at runtime. The static type still says `Trivia` is possible, but the actual runtime values never include it.

**Consequence:** The static type is broader than reality. `visit_items` (`fltk2gsm.py:43`) iterates `items.children` where the second element of each tuple is typed `Item | Trivia | Span`, but at runtime with `capture_trivia=False` the only values are `Item` (label `ITEM`) and `Span` (labels `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`).

---

## 4. Could the Union Be Tightened? What Blocks the Discriminant Approach?

**What blocks `kind`-based narrowing:**

The union contains `fltk.fegen.pyrt.terminalsrc.Span`, which is a plain library dataclass — `Span(start: int, end: int)`. It carries no `NodeKind` discriminant, no `.kind` attribute, and no `Label` enum. It is a terminal type, not a generated CST node. A `kind`-switch that distinguishes `Item` from `Span` is therefore impossible without an `isinstance` check or a `cast`.

`visit_items` (`fltk2gsm.py:65–80`) does not need to inspect the value of a separator child at all — it only cares about the **label** (`NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`). The current code (`_` discards the separator value, uses only the label). So in practice the heterogeneity of the value type is irrelevant for `visit_items`; the `cast` needed is only on the `Item`-labeled child (`assert isinstance(item, self.cst.Item)`), not on separator children.

**Could `Trivia` be removed from the static type?**

Yes, if `CstGenerator.model_for_rule` respected `context.capture_trivia` — i.e., only incorporated `"_trivia"` into `model.types` when `capture_trivia=True`. This would make the static type match the runtime reality for `capture_trivia=False`. The generator already has access to `self.context.capture_trivia`; this is a gap in the generator, not a fundamental constraint.

**Could `Span` be represented differently?**

Separators could be given a dedicated wrapper type (e.g. `SeparatorToken`) that carries a `kind` discriminant, making the union `Item | Trivia | SeparatorToken` with all three types having a `kind` field. That would enable kind-based narrowing. However, `Span` is an intentional primitive — it is the same type used for all terminal matches throughout the system. Wrapping it would add a layer.

**Is the union `Item | Trivia | Span` accurate?**

With `capture_trivia=False` (the committed fegen configuration), the **runtime** union is `Item | Span`. The static type `Item | Trivia | Span` is **broader than reality** due to the generator not conditioning on `capture_trivia`. The union is not narrower than reality — there is no `Span` member that is impossible; `Span` children (the labeled separator tokens) are genuinely present.

The discriminant approach is blocked specifically by `Span` lacking a `NodeKind`. The `Trivia` member is spurious under `capture_trivia=False` and could be removed with a generator change. Removing `Trivia` would yield `Item | Span`, which is still heterogeneous and still requires either `isinstance` or label-based dispatch, since `Item` and `Span` share no common discriminant field.
