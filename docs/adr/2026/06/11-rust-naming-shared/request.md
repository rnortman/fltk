# Request: single source of truth for generated Rust enum naming

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Pure refactor (no generated-output change).

**Origin:** TODO.md slug `rust-naming-shared`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 6).

**USER DECISION (verbatim):** "Do (after or as part of parser-bindings-name-collision refactoring)" — i.e., sequence this after or within the module-split work at `docs/adr/2026/06/11-rust-bindings-module-split/`. If line numbers below have shifted by the time this runs, re-locate by symbol name.

## Background

The `{ClassName}Child` naming convention for generated Rust child enums is constructed independently in FOUR places (validation found one more than the TODO claimed — see `exploration.md` in this dir):
- `gsm2parser_rs.py:197` — `_child_enum_name`: `self._class_name(rule_name) + "Child"` (TODO comment at 193).
- `gsm2tree_rs.py:497` — inline `f"{class_name}Child"` in `_child_enum_block`.
- `gsm2tree_rs.py:621` — inline, in `_node_block`.
- `gsm2tree_rs.py:1058` — inline, in `_label_type_info`.

A rename in one place without the others produces parser code referencing nonexistent CST enum names, caught only at `cargo` compile time of generated output — far from the mistake.

Facts that make this easy:
- `gsm2parser_rs.py` already imports `RustCstGenerator` (line 23) and holds `self._cst` (line 82); it already delegates `_class_name` (line 188-190) and `_label_type_info` (line 201) through it. Zero new coupling needed; dep direction `gsm2parser_rs → gsm2tree_rs` already exists, no cycle.
- `_label_enum_rust_name` (`gsm2tree_rs.py:400-406`) is already a method — the `Label` side is fine; only the `Child` suffix is duplicated.

## Fix shape

Add one `child_enum_name(rule_name or class_name)` method on `RustCstGenerator`; point all four sites at it (parser side via `self._cst`).

## Constraints / non-goals

- Generated output must be byte-identical before/after (pure refactor) — diff regenerated fixtures to prove it.
- Non-goal: `_rust_str_lit` sharing (slug `rust-str-lit-shared` was triaged Delete — unreachable bug; see `exploration-str-lit-context.md` in this dir for why). Do not expand scope to it.
- Coordinate with the module-split work if concurrent; this change is small enough to ride along or follow.

## Verification expectations

- Regenerated outputs byte-identical (or, if the module-split landed first, identical modulo that work's changes).
- Full test suite; `make fix`; `uv run pytest` clean.
