# Adversarial Validation: `extend-children-owned` TODO

Concise. Precise. No fluff.

## Claim 1: Call sites exist in `_gen_item_multiple` and `_gen_append_code`

**CONFIRMED.**

`gsm2parser_rs.py:712`:
```python
lines.append("            result.extend_children(&one_result.result);")
```
Inside `_gen_item_multiple`, the `+`/`*` loop body, guarded by `if one_is_inline and item.disposition != gsm.Disposition.SUPPRESS`.

`gsm2parser_rs.py:830`:
```python
return f"result.extend_children(&{item_var}.result);"
```
Inside `_gen_append_code`, the `if item_fn.inline_to_parent:` branch. This covers non-multiple inline-to-parent items (sub-expressions in single/optional context).

The TODO comment itself appears at `gsm2parser_rs.py:706-710` inside `_gen_item_multiple`.

Generated fixture confirms both patterns in real output:

- `tests/rust_parser_fixture/src/parser.rs:404`: `result.extend_children(&item0.result);` — sub-expression inline-to-parent (single item in alternative context, `parse_items__alt0`).
- `tests/rust_parser_fixture/src/parser.rs:468`: `result.extend_children(&item0.result);` — `*` loop result assigned to alternative parent (`parse_zero_items__alt0`).
- `tests/rust_parser_fixture/src/parser.rs:943,1039`: same pattern for `grouped` and `rec_via_sub` rules.

The `+`/`*` loop path calls it as `result.extend_children(&one_result.result)` (loop variable, `gsm2parser_rs.py:712`). The alternative path calls it as `result.extend_children(&item_var.result)` (`gsm2parser_rs.py:830`).

## Claim 2: Donor is immediately dropped after the call

**CONFIRMED for the `*`/`+` loop path. NUANCED for the inline-to-parent alternative path.**

`_gen_item_multiple` (`gsm2parser_rs.py:667-730`): the loop variable `one_result` holds `ApplyResult<cst::ParentClass>` (the plain value type, not `Shared<>`). After `extend_children(&one_result.result)`, `one_result` goes out of scope at the loop iteration boundary. No other reference is taken. The donor is value-typed (`cst::ParentClass`, not `Shared<cst::ParentClass>`), so there is no packrat cache retaining it.

`_gen_append_code` (`gsm2parser_rs.py:810-832`): the `item_var` binding is `ApplyResultt<cst::ParentClass>` (verified by `_gen_item_single_or_optional` returning `parent_class_name` for inline items). After the `extend_children` call the generated code moves to `pos = item_var.pos;` (already done before `_gen_append_code` is called — see `_gen_alternative` lines 534-539) so the struct is only used for `.pos` and `.result`. The binding is local to the `if let Some(...) =` arm and drops at the end of that arm.

**Critical distinction**: inline-to-parent functions return `ApplyResult<cst::NodeType>` (the plain data struct), not `ApplyResult<Shared<cst::NodeType>>`. These are never stored in the packrat `Cache<Shared<T>>`. The `Cache<T>` at `memo.rs:62` stores `Shared<T>`; only the memoized top-level rule parsers (those with `apply__` wrappers) produce `Shared`. Inline-to-parent sub-functions are never memoized — `_cache_parser_info` is called with `memoize=False` (default) at `gsm2parser_rs.py:511, 646, 673, 786`. **Therefore the packrat cache does not retain a `Shared` alias to the donor node; the donor is uniquely owned at the call site.**

**The `+`/`*` loop donor (`one_result`) is unambiguously uniquely owned** — it is a freshly constructed `cst::NodeType` value (local variable, never wrapped in `Shared` before extend_children is called). `_gen_item_multiple` returns `ApplyResult<cst::ParentClass>` (the plain struct, not Shared): `gsm2parser_rs.py:686`.

## Claim 3: The cost is one Arc clone per child (atomic inc+dec)

**CONFIRMED.**

`gsm2tree_rs.py:1027`:
```python
lines.append("    pub fn extend_children(&mut self, other: &Self) {")
lines.append("        self.children.extend(other.children.iter().cloned());")
```
`children` is `Vec<(Option<LabelEnum>, ChildEnum)>`. `Clone` on `ChildEnum` is the auto-derived `Clone` which clones each variant. Node-typed variants are `ChildEnum::SomeNode(Shared<SomeNode>)`, and `Clone` on `Shared<T>` is `Arc::clone` (`shared.rs:95-97`), which is an atomic increment. When `extend_children` returns and the donor drops, each `Arc` is decremented again (drop of the donor's `children` Vec). This is one atomic increment + one atomic decrement per node-typed child.

Span-typed children (`ChildEnum::Span(Span)`) are copied by value — Span is a plain struct (start/end fields + `Arc<SourceText>`), so even Span clones do an Arc increment on the source text. However the main cost identified in the TODO is node-typed children.

`Vec::append` (the proposed alternative) moves elements out of one Vec into another via `ptr::copy` — no reference count changes.

## Claim 4: "Blocked on `gsm2tree_rs.py` adding the method" — is this accurate?

**PARTIALLY ACCURATE but overstated as a blocker.**

The method `extend_children_owned` does not exist in `gsm2tree_rs.py`. It would need to be added to `_node_block` (the plain `impl ClassName` block, `gsm2tree_rs.py:963-1034`) alongside the existing `extend_children`. The generated `.pyi` stub (`generate_pyi`, `gsm2tree_rs.py:276`) and the protocol module would also need updating for the new method.

The TODO says "blocked on `gsm2tree_rs.py` adding the method." This is accurate in the sense that the generated CST API must have the method before the parser generator can emit calls to it. However it is not an external or organizational blocker — both `gsm2tree_rs.py` and `gsm2parser_rs.py` live in the same file set, and the change is self-contained. "Blocked" overstates the dependency; it is more accurate to say "requires a coordinated change to both generators in the same commit."

## Claim 5: Memoization/packrat caching could mean the donor is NOT uniquely owned

**FALSE for all identified call sites.** (This is the most important adversarial question.)

The inline-to-parent functions (`parse_X__altN`, `parse_X__altN__itemM__alts`, `parse_X__altN__itemM` for multiple items) are never memoized. Their return type is `Option<ApplyResult<cst::ParentClass>>` — the plain data struct, not `Shared<>`. The packrat cache type is `Cache<Shared<NodeT>>` (`memo.rs:62`). Non-`Shared` return types are structurally excluded from the cache.

Only the top-level rule parsers (those with `apply__` wrappers and a `cache__` field) are memoized, and they store/return `Shared<T>`. Cache hits clone the `Shared<T>` (`memo.rs:287`, comment at `memo.rs:174`: "for generated code `T = Shared<NodeT>`, so a hit is an Arc clone"). Inline-to-parent nodes are created fresh at each call and never put into the packrat cache.

**Conclusion: the donor is always uniquely owned (strong_count == 1) at every `extend_children` call site in the hot parse path.**

## Claim 6: "Re-open only with profiling evidence" — does any profiling evidence exist?

**No profiling evidence exists in-tree.** `grep` over all `.md`, `.toml`, `.rs` for `profiling`, `benchmark`, `flamegraph`, `criterion` found no benchmark harness or profiling results. The `docs/adr/2026/05/28-pyo3-phase4-runtime-integration/requirements.md:51` explicitly notes: "No benchmark acceptance criteria are set here." The TODO was added without profiling data; it defers re-opening to when profiling evidence exists.

## Claim 7: Is this papering over a symptom of a deeper problem?

**The deeper issue is that extend_children is called on value-typed intermediates that could simply be moved/consumed.** The `_gen_item_multiple` loop returns a `cst::ParentClass` by value; calling `extend_children(&one_result.result)` and then immediately dropping `one_result` is the pattern. The generator could instead call `extend_children_owned(one_result.result)` (consuming) using `Vec::append`. The "deeper problem" is not a design flaw but the absence of a consuming variant of the API — the current Rust API only offers `extend_children(&Self)` (borrow), which forces a clone even when ownership could be transferred.

There is no deeper architectural issue: the nodes are not aliased, the packrat cache does not hold them, and the call pattern is correct. The optimization is purely mechanical.

## Summary of verdicts

| Claim | Verdict |
|-------|---------|
| Call sites in `_gen_item_multiple` and `_gen_append_code` exist | Confirmed |
| Donor is uniquely owned / immediately dropped | Confirmed |
| Arc clone per child (atomic inc+dec) is the cost | Confirmed |
| "Blocked on gsm2tree_rs.py" is accurate | Overstated; same-PR change, no external blocker |
| Packrat caching could alias the donor | False; inline-to-parent functions are never memoized |
| Profiling evidence exists in-repo | None found |
| Deeper architectural problem | No; straightforward API gap |

## Key source locations

- `gsm2parser_rs.py:706-712`: TODO comment + `extend_children` call in `_gen_item_multiple` (`+`/`*` loop)
- `gsm2parser_rs.py:824-830`: `extend_children` call in `_gen_append_code` (inline-to-parent single item)
- `gsm2tree_rs.py:1026-1028`: `extend_children` implementation (`iter().cloned()`)
- `crates/fltk-cst-core/src/shared.rs:93-97`: `Clone` on `Shared<T>` is `Arc::clone`
- `crates/fltk-parser-core/src/memo.rs:62`: `Cache<T> = HashMap<i64, MemoEntry<T>>` — stores `Shared<T>`, not plain `T`
- `tests/rust_parser_fixture/src/parser.rs:404,468,943,1039`: confirmed generated call sites
