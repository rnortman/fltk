# Exploration: TODO(cst-protocol-label-free) — Adversarial Verification

Concise. Precise. Token-dense. No fluff.

## Claim in TODO

> Protocol classes for label-free CST nodes declare `children: list[tuple[None, T]]` while
> label-bearing nodes use `list[tuple[Optional[Label], T]]`. This asymmetry means generic code
> iterating children of arbitrary node types must case-split on whether the node has labels,
> which is not inferrable from the Protocol type alone. Fix: introduce a vacuous `Label` class
> for label-free nodes (or a `_NoLabel = None` alias) so all node `children` share the same
> tuple shape. Location: `fltk/fegen/gsm2tree.py` (`_protocol_class_for_model`).

---

## Fact 1 — Asymmetry is real and confirmed

`fltk/fegen/gsm2tree.py:518–583` (`_protocol_class_for_model`):

- **Label-bearing nodes** (lines 553–554):
  ```python
  klass.body.append(pygen.stmt(f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"))
  ```
- **Label-free nodes** (lines 556–561):
  ```python
  # TODO(cst-protocol-label-free): label-free nodes use tuple[None, T] rather than
  # tuple[Label | None, T], creating an asymmetry with label-bearing nodes.
  klass.body.append(pygen.stmt(f"children: list[tuple[None, {child_annotation}]]"))
  ```

The `child()` return type also diverges: label-bearing → `tuple[typing.Optional[Label], T]`
(line 578), label-free → `tuple[None, T]` (line 580). `append` and `extend` signatures likewise:
`label_annotation = "typing.Optional[Label]" if labels else "None"` (line 563).

**Concrete dataclass generator (`py_class_for_model`, lines 200–234) does NOT have this
asymmetry**: it unconditionally emits a `Label(enum.Enum)` class and uses
`list[tuple[typing.Optional[Label], T]]` regardless of whether there are any labeled items.

## Fact 2 — When label-free protocol nodes are produced

The branching condition is `labels = sorted(model.labels.keys())` at line 525. `model.labels` is
populated in `model_for_items` (lines 364–382): only items where `item.label` is set (line 379)
contribute labels.

**Critical upstream behavior** — `fltk2gsm.py:94–96**:
```python
label = self.visit_identifier(cst_label).value if (cst_label := item.maybe_label()) else None
if label is None and isinstance(term, gsm.Identifier):
    label = term.value
```
Every item whose term is a rule reference (`gsm.Identifier`) is **auto-labeled** with the
referenced rule's name. This means all Identifier-referencing items in every grammar rule get a
label, even without an explicit `label:` prefix.

**Disposition default** (`fltk2gsm.py:98–103`): items with no explicit label AND a non-Identifier,
non-Sequence term (i.e., a Literal or Regex) default to `SUPPRESS` unless an explicit `$`
disposition is present. Suppressed items are skipped in `model_for_items` (line 367–369) and
contribute neither to `model.types` nor `model.labels`.

**Net result**: a label-free protocol node requires ALL non-suppressed included items to be
Literal or Regex terms with explicit `$` disposition and NO explicit `label:` prefix.

## Fact 3 — No in-tree grammar triggers the label-free protocol code path

Every in-tree generated grammar (`fegen.fltkg`, `bootstrap.fltkg`, `toy.fltkg`,
`unparsefmt.fltkg`, `test_data/phase4_roundtrip.fltkg`) produces only label-bearing protocol
nodes. Verified:

- `fltk/fegen/fltk_cst_protocol.py`: all 14 Protocol node classes have a `Label` subclass and
  `children: list[tuple[Label | None, ...]]`. Zero occurrences of `tuple[None,`.
- `fltk/fegen/bootstrap_cst.py`, `fltk/unparse/toy_cst.py`,
  `fltk/unparse/unparsefmt_cst.py`: likewise all `Label | None`.

The `tuple[None, T]` emit path (`gsm2tree.py:561`) is latent — unreachable by any in-tree grammar
but reachable by downstream consumer grammars that use explicit `$` disposition on literal/regex
items with no label prefix.

## Fact 4 — Proposed fix: correctness and downstream annotation impact

**Proposed fix**: emit a vacuous `Label` class for label-free protocol nodes, making `children:
list[tuple[Label | None, T]]` uniform.

**Correctness**: the fix is sound. The concrete dataclass already always emits `Label | None`,
so the Protocol would match the concrete class surface. Runtime values for label-free nodes would
still always be `None` in the label position; the only change is the static type widening from
`None` to `Label | None`.

**Downstream annotation churn assessment**:

1. **Consumers using concrete CST classes only**: zero churn — `py_class_for_model` already
   uses `Label | None` unconditionally.

2. **Consumers using Protocol types for label-free nodes**: the `children` type would change
   from `list[tuple[None, T]]` to `list[tuple[Label | None, T]]`. Any downstream code that
   statically annotated against `tuple[None, T]` would need to update. However:
   - The label-free protocol code path is currently latent (no in-tree grammar triggers it).
   - Out-of-tree grammars that do trigger it are the only affected consumers.
   - The change is widening (more permissive at the label position), so runtime behavior is
     unchanged; only static type annotations at call sites would need update.
   - `list` is invariant in Python typing, so `list[tuple[None, T]]` is NOT a subtype of
     `list[tuple[Label | None, T]]` — a type-checked reassignment would fail until updated.

3. **`child()`, `append()`, `extend()` signatures**: same narrowing → widening change at the
   label parameter/return type. Label-free protocol's `append(child, label: None = None)` would
   become `append(child, label: Label | None = None)`. Callers passing `None` explicitly remain
   valid; callers annotating the return of `child()` as `tuple[None, T]` would need updating.

**No variance/type-checking blocker**: the concrete dataclass already uses `Label | None` for
label-free nodes; the Protocol adopting the same shape would remove the current mismatch, not
introduce a new one.

## Fact 5 — The `_NoLabel` alias variant

The alternative (`_NoLabel = None` module-level alias) would produce
`list[tuple[_NoLabel | None, T]]` which simplifies to `list[tuple[None, T]]` since
`_NoLabel | None` is `None | None` = `None`. This does NOT unify the shape — it is a no-op
change that leaves the asymmetry intact under static analysis. Only the vacuous-Label-class
approach genuinely unifies.

## Summary

| Claim | Verdict |
|---|---|
| `_protocol_class_for_model` emits `tuple[None, T]` for label-free nodes | **Confirmed** (gsm2tree.py:561) |
| `tuple[Optional[Label], T]` for label-bearing nodes | **Confirmed** (gsm2tree.py:554) |
| Asymmetry is real | **Confirmed** |
| Any in-tree grammar triggers the label-free path | **False** — path is latent |
| Auto-labeling masks the issue for Identifier terms | **Confirmed** (fltk2gsm.py:95–96) |
| Vacuous-Label fix unifies shape without breaking variant | **Yes, but widens downstream annotation for label-free nodes** |
| `_NoLabel = None` alias fixes the asymmetry | **No** — `None \| None = None`, no-op |
| Fix causes annotation churn for in-tree consumers | **No** — no in-tree label-free protocol nodes exist |
| Fix causes annotation churn for out-of-tree consumers | **Potentially yes**, for consumers with label-free grammar rules and typed Protocol usage |
