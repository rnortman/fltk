# Request: rust-generated-ident-collisions — generation-time cross-rule identifier collision check

Style: concise, precise, no padding, no preamble. Self-contained; downstream agents see only this dir. Validated exploration: `exploration.md` (same dir) — adequate; skip the explore phase and proceed to requirements.

## Type of work

New validation feature in the Rust CST generator (`fltk/fegen/gsm2tree_rs.py`). Pure Python change + tests. No generated-API change for valid grammars.

## Background

For each grammar rule, the Rust generator derives several module-level Rust identifiers from the rule name via `snake_to_upper_camel` (`fltk/iir/py/naming.py:22` formula; `gsm2tree.py:46-47` entry point). Per rule with class name `CN`:

| Identifier | Formula | Emission site |
|---|---|---|
| Node data struct | `CN` | `gsm2tree_rs.py:731` |
| PyO3 handle struct | `Py{CN}` | `gsm2tree_rs.py:709` |
| Child value enum | `{CN}Child` | `gsm2tree_rs.py:537-543` |
| Label enum | `{CN}Label` | `gsm2tree_rs.py:454` |

Nothing checks collisions *between rules*. Verified collision classes (all produce Rust `E0428` "name defined multiple times" — an opaque cargo error with no pointer back to the grammar):

1. Rule `foo_child` → struct `FooChild` collides with rule `foo`'s child enum `FooChild`.
2. Rule `foo_label` → struct `FooLabel` collides with rule `foo`'s label enum `FooLabel`.
3. Rule `py_foo` → struct `PyFoo` collides with rule `foo`'s handle `PyFoo`.
4. Rule `drop_worklist_item` → struct `DropWorklistItem` collides with the module-level `DropWorklistItem` enum (`gsm2tree_rs.py:1954-1956`). This class is missing from the existing reserved-name set — a gap the original TODO did not mention.

Existing prior art: the fixed reserved-set check `_RESERVED_CLASS_NAMES` (`gsm2tree_rs.py:36-41`: `NodeKind`, `Span`, `Shared`, `CstError`) enforced in `RustCstGenerator.__init__` at `gsm2tree_rs.py:80-83`, raising `ValueError` with a descriptive message. The cross-rule check is the natural extension at the same point.

Python backend has none of these collision classes (no module-level Child/Label/Py/DropWorklistItem types) — validated.

## Fix shape (user-approved direction)

At generation time, in `RustCstGenerator.__init__`:
- Compute every top-level Rust identifier the generator will emit for every rule (`CN`, `Py{CN}`, `{CN}Child`, `{CN}Label` — formulas above; all pure functions of the rule name, available before emission).
- Detect duplicates across the whole set and raise `ValueError` before any code is emitted. The error message must name **both colliding grammar rules** and **which derived identifiers collide** (actionable: tells the user which rule to rename) — same spirit as the existing `_RESERVED_CLASS_NAMES` message.
- Add `"DropWorklistItem"` to `_RESERVED_CLASS_NAMES`.

## Constraints / non-goals

- Valid (non-colliding) grammars must generate byte-identical output to today — this is a check, not a renaming scheme. Do NOT invent name-mangling/renaming to "resolve" collisions; reject with a clear error.
- Python backend out of scope.
- Label enums are emitted only for rules that have labels, and child enums only when applicable — the design should decide whether to flag collisions only for identifiers actually emitted for that grammar or conservatively for all derivable names; either is acceptable if deliberate and documented.

## Verification expectations

- TDD per CLAUDE.md: failing tests first.
- Tests covering each collision class (1–4): grammar with `foo` + `foo_child`, `foo` + `foo_label`, `foo` + `py_foo`, and a `drop_worklist_item` rule — each raises `ValueError` naming the culprits. Plus a non-colliding grammar still generates.
- Existing in-tree grammars (fegen self-hosting, test fixtures) still generate unchanged.
- Full suite: `uv run pytest`; `make check` clean.
- On completion remove the TODO: `TODO.md` entry `rust-generated-ident-collisions`, code comment `TODO(rust-generated-ident-collisions)` at `gsm2tree_rs.py:33-35`.
