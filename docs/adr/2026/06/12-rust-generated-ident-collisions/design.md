# Design: rust-generated-ident-collisions — cross-rule Rust identifier collision check

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

Requirements: `request.md` (same dir). Exploration: `exploration.md` (same dir). This doc does not restate them.

## Root cause / context

The Rust CST generator derives up to four module-level Rust identifiers per grammar rule from `CN = snake_to_upper_camel(rule_name)`: node struct `CN`, handle `Py{CN}`, child enum `{CN}Child`, label enum `{CN}Label`. Nothing checks collisions between rules, so e.g. rules `foo` + `foo_child` emit `pub enum FooChild` and `pub struct FooChild` in the same module → Rust `E0428` with no pointer back to the grammar. Prior art is the fixed-set check `_RESERVED_CLASS_NAMES` enforced in `RustCstGenerator.__init__` (`fltk/fegen/gsm2tree_rs.py:80-83`), which raises `ValueError` naming the rule and collision target. That set also misses `DropWorklistItem` (emitted at `gsm2tree_rs.py:1946`).

Emission facts that drive the design (verified in `gsm2tree_rs.py:generate`, lines 289-296):

- Node struct `CN`, handle `Py{CN}`, and child enum `{CN}Child` are emitted **unconditionally** for every rule (`_child_enum_block` is called for every rule regardless of children; `_node_block` always emits both struct and handle).
- Label enum `{CN}Label` is emitted **only when the rule has labels** (`_label_enum_block` returns `""` for label-less rules, line 470-471).
- `DropWorklistItem` is emitted only when the child-class union is non-empty (`_drop_block`, line 1936).
- The generator iterates `self.grammar.rules` = the trivia-augmented grammar, which includes the auto-added `_trivia` rule (`gsm.TRIVIA_RULE_NAME`, CN `Trivia`). Its derived identifiers participate in collisions like any other rule's.
- `CstGenerator.__init__` populates `rule_models` for every rule (`gsm2tree.py:44`), so per-rule label sets are available inside `RustCstGenerator.__init__` after `self._py_gen` is constructed.

A non-obvious extra collision class falls out of the same mechanism: two **distinct** rule names can derive the same `CN` (`snake_to_upper_camel` is not injective: `foo_bar` and `foo__bar` both → `FooBar`), duplicating every identifier family. The set-based check below catches this for free.

Within a single rule, the four families cannot collide with each other (`Py{CN}`, `{CN}Child`, `{CN}Label` differ from `CN` and from each other by fixed-length affixes), so the check is purely cross-rule.

## Proposed approach

All changes in `fltk/fegen/gsm2tree_rs.py` plus tests; no generated-output change for grammars that remain accepted. Exactly one previously-compiling class becomes newly rejected: a rule named `drop_worklist_item` in a grammar with no node-typed children anywhere (§1, request-directed — see the trade-off discussion there).

### 1. Add `DropWorklistItem` to `_RESERVED_CLASS_NAMES`

Entry: `"DropWorklistItem": "the generated DropWorklistItem drop-worklist enum"`.

This is deliberately **conservative**: a rule named `drop_worklist_item` is rejected even in a grammar where the enum would not be emitted (no node-typed children anywhere). Rationale: reserved-set semantics are unconditional for the existing four entries; conditioning on `_child_class_union()` would couple validation to emission internals; and the false-positive surface (a grammar with a rule literally named `drop_worklist_item` and zero node-typed children) is negligible. User-approved direction per `request.md`.

### 2. Single source of truth for the handle name

Add a static helper alongside `child_enum_name` / `_label_enum_rust_name`:

```python
@staticmethod
def py_handle_name(class_name: str) -> str:
    return f"Py{class_name}"
```

Use it in the new check and at the handle-definition site in `_node_block` (`py_handle = f"Py{class_name}"`, line 709). Other `f"Py{child_cls}"` interpolations (referenced-handle usages inside `_child_enum_block` etc.) stay as-is; the drift test in the test plan guards them. Output is byte-identical (pure refactor of an f-string).

### 3. Cross-rule collision check in `RustCstGenerator.__init__`

Runs after the existing per-rule validation loop (regex, `_RESERVED_CLASS_NAMES`, `_RESERVED_LABELS`), before any emission. Existing error precedence is preserved: a rule that trips a reserved-name check reports that error, never reaches the new check.

Algorithm (one pass over `self.grammar.rules`, then duplicate detection):

```python
claims: dict[str, list[tuple[str, str]]] = {}   # ident -> [(rule_name, family_desc)]
for rule in self.grammar.rules:
    cn = self._py_gen.class_name_for_rule_node(rule.name)
    claims.setdefault(cn, []).append((rule.name, "node struct"))
    claims.setdefault(self.py_handle_name(cn), []).append((rule.name, "Python handle struct"))
    claims.setdefault(self.child_enum_name(cn), []).append((rule.name, "child value enum"))
    model = self._py_gen.rule_models.get(rule.name)
    if model is not None and model.labels:
        claims.setdefault(self._label_enum_rust_name(cn), []).append((rule.name, "label enum"))
```

Any identifier with ≥2 claimants is a collision. Raise a single `ValueError` reporting **all** collisions, sorted by identifier (deterministic messages). Per collision, the message names the identifier and every claimant `(rule, family)` pair — actionable: tells the user exactly which rules to rename. Format (one line per collision, joined with newlines):

```
Generated Rust identifier 'FooChild' collides: node struct for rule 'foo_child' vs child value enum for rule 'foo'; rename one of these rules
```

When a claimant is the auto-added trivia rule, annotate it as `rule '_trivia' (auto-generated trivia rule)` so users who never wrote `_trivia` are not mystified. The annotation is keyed on whether the rule was actually auto-added, not on the name: `gsm.add_trivia_rule_to_grammar` returns the grammar unchanged when the user already defines `_trivia` (`gsm.py:425`), and a user-written `_trivia` must be reported as an ordinary rule. The raw pre-augmentation `grammar` argument is still in scope in `__init__`; annotate only when `gsm.TRIVIA_RULE_NAME not in grammar.identifiers`.

Design decisions, called out:

- **Emitted-only semantics for `{CN}Label`** (the request leaves this open): the label enum is claimed only for rules that actually have labels. Conservative claiming would reject grammars that compile fine today (rule `foo` with no labels + rule `foo_label`) — a backward-compatibility break for out-of-tree consumers, which CLAUDE.md forbids absent explicit need. Trade-off accepted: later adding a label to `foo` flips such a grammar from valid to rejected, but the failure then surfaces at generation time with an actionable message naming both rules — strictly better than today's `E0428`. For the other three families, emitted-only and conservative coincide (always emitted).
- **`rule_models.get()` rather than indexing**: a missing model is an invariant violation that `_rule_info()` already diagnoses with a precise `RuntimeError`; the collision check must not preempt that diagnostic with a `KeyError`. Treat missing as label-less.
- **Reserved names are not seeded into `claims`**: the operative invariant is that no current reserved name (`NodeKind`, `Span`, `Shared`, `CstError`, `DropWorklistItem`) starts with `Py`, ends with `Child`, or ends with `Label`, so no derived non-`CN` identifier (`Py{CN}`, `{CN}Child`, `{CN}Label`) can equal a reserved name; direct `CN`-vs-reserved is already covered by the existing per-rule check. Folding them in would duplicate reporting for no coverage gain. This invariant is a constraint on future `_RESERVED_CLASS_NAMES` additions — record it in the comment above the dict (a future Py-prefixed reserved name, e.g. `PySpan`, would need seeding into `claims` to keep coverage).

### 4. TODO removal

- Replace the `TODO(rust-generated-ident-collisions)` comment at `gsm2tree_rs.py:33-35` with a short comment noting cross-rule collisions are checked in `__init__` below.
- Delete the `rust-generated-ident-collisions` entry from `TODO.md` (around line 40).

## Edge cases / failure modes

- **Rule `foo` without labels + rule `foo_label`**: accepted (emitted-only). Positive test required.
- **Same-`CN` rules (`foo_bar` + `foo__bar`)**: caught as node-struct/node-struct collision (and every other family); without this check the output would be `E0428` on the struct itself.
- **User rule colliding with `_trivia` derivatives** (e.g. user rule `trivia` → CN `Trivia` duplicates `_trivia`'s CN; or `trivia_child`): caught; message carries the auto-generated annotation only when `_trivia` was auto-added. A user-defined `_trivia` (suppresses augmentation, `gsm.py:425`) is reported as an ordinary rule with no annotation.
- **Three or more claimants on one identifier**: all listed in the message.
- **Multiple independent collisions**: all reported in one `ValueError` (users fix a grammar in one pass instead of error-whack-a-mole).
- **Formula drift**: the check predicts names via the same helpers the emitters use for `{CN}Child`/`{CN}Label`/`Py{CN}` (definition site); remaining inline `Py{...}` interpolations are guarded by the prediction-vs-output consistency test below.
- **Generated-output stability**: the check raises before emission and the only emission-path edit is the f-string→helper refactor at line 709; existing self-hosting and fixture grammars must regenerate byte-identically (covered by existing regen tests + `make check`).

## Test plan

TDD: write these first, watch them fail, then implement. New tests in `tests/test_gsm2tree_rs.py`, following the existing `TestReservedClassNameRejection` conventions (`_make_single_rule_grammar` helper; assert error text names rule and identifier).

1. Extend the existing reserved-name parametrize with `("drop_worklist_item", "DropWorklistItem", "DropWorklistItem")`.
2. New class `TestCrossRuleIdentifierCollisions` with a multi-rule grammar helper (labeled regex items, so rules have labels by default):
   - `foo` + `foo_child` → `ValueError`; message contains both rule names and `FooChild`.
   - `foo` + `foo_label` (where `foo` has a labeled item) → `ValueError`; both rule names and `FooLabel`.
   - `foo` + `py_foo` → `ValueError`; both rule names and `PyFoo`.
   - `foo_bar` + `foo__bar` → `ValueError`; both rule names and `FooBar` (non-injective `CN`).
   - Emitted-only positive case: `foo` built with an **unlabeled** item + `foo_label` → accepted; `generate()` output contains `pub struct FooLabel` (the rule's node struct) and not `pub enum FooLabel {` — assert with the trailing `{`, because if `foo_label` itself has labels it emits `pub enum FooLabelLabel`, which contains the bare substring `pub enum FooLabel` and would make a brace-less absence assertion fail spuriously.
   - Trivia annotation: user rule `trivia` (no user `_trivia`) → message annotates `_trivia` as auto-generated; user-defined `_trivia` + user rule `trivia` → message names both rules with no auto-generated annotation.
   - Multiple collisions reported at once: grammar with `foo`, `foo_child`, `bar`, `bar_child` → single `ValueError` whose text contains both `FooChild` and `BarChild`.
   - Non-colliding multi-rule grammar → constructs and `generate()` succeeds.
3. Prediction-vs-output consistency (drift guard): for a small grammar with labels and node-typed children, compute the claimed identifier set per rule and assert each appears in `generate()` output as the corresponding `pub struct {ident}` / `pub enum {ident}` definition (label enum asserted only for labeled rules).
4. Existing suite green: fegen self-hosting and fixture grammars regenerate unchanged; `uv run pytest`; `make check` clean.

## Open questions

None. The one judgment call the request delegated (emitted-only vs conservative for conditionally-emitted identifiers) is decided and documented above: emitted-only for `{CN}Label`, conservative for the fixed reserved name `DropWorklistItem`.
