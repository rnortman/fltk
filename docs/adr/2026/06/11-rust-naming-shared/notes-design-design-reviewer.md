# Design review: rust-naming-shared

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Reviewed: `design.md` against `request.md`, `exploration.md`, `exploration-str-lit-context.md`, and source at base commit 7ddec4a.

## Verification summary (all checked against code)

- Four duplication sites: `gsm2parser_rs.py:192-197` (`_child_enum_name`, TODO comment 193-196, callers 550/965), `gsm2tree_rs.py:497` (`_child_enum_block`), `:621` (`_node_block`), `:1058` (`_label_type_info`) — all confirmed verbatim. Repo-wide grep finds no fifth construction site.
- Dep direction: `gsm2parser_rs.py:23` imports `RustCstGenerator`; `self._cst` at line 82; existing delegations `_class_name` (188-190) and `_label_type_info` (199-201) — confirmed.
- Label side already single-source: `_label_enum_rust_name` (399-406), `_label_enum_python_name` (408-411); parser side never constructs label enum names — confirmed.
- TODO bookkeeping: `TODO.md` entry header at line 68; the only `TODO(rust-naming-shared)` code comment is `gsm2parser_rs.py:193` — confirmed by grep.
- Prose-only `<Name>Child` mentions left alone (489, 1044, 1049) — confirmed; correctly excluded.
- Test plan: `make gencode` target (Makefile:148) covers exactly the listed outputs including `crates/fltk-cst-spike/src/cst.rs` copy; `fltk/fegen/test_gsm2parser_rs.py` and `tests/test_gsm2tree_rs.py` exist — confirmed.
- Requirements coverage: byte-identical constraint (helper returns the identical string; regen-diff verification), four call-site edits, TODO removal, non-goal `_rust_str_lit` respected (no shared module created), sequencing per user decision — all covered. No scope creep; explicitly declines to publicize `_label_enum_*` or add a tautological test. Consistent with CLAUDE.md (no generated-surface change).

## Findings

### design-1

Section: "Sequencing with module-split" — "The module-split touches registration/`lib.rs` emission (`gsm2parser_rs.py:813-923`, `gsm2tree_rs.py:1517-1531`); this change touches naming helpers and three enum-name assignments — disjoint regions".

What's wrong: the module-split touch-point list is incomplete. Per `docs/adr/2026/06/11-rust-bindings-module-split/design.md` (lines 90-104, 131-132), that work also adds a `_RESERVED_CLASS_NAMES` check inside `RustCstGenerator.__init__` (`gsm2tree_rs.py:56-80`), updates the pyi safety comment (`gsm2tree_rs.py:142-143`), adds a new TODO comment in `gsm2tree_rs.py`, and removes the `TODO(parser-bindings-name-collision)` comment (`gsm2parser_rs.py:816-820`).

Why: source-backed by the module-split design's own "files touched" table (its line 131-132) listing `gsm2tree_rs.py` and `gsm2parser_rs.py` edits beyond registration emission.

Consequence: low. The additional regions (`__init__` ~56-80, ~142-143, ~816-820) are still disjoint from this change's edit regions (192-197, 395-411, 497, 621, 1058), so the "conflicts unlikely" conclusion stands; the misstatement could only mislead an implementer estimating rebase risk. No requirement is affected.

Suggested fix (optional): amend the sentence to "the module-split touches `__init__` validation, pyi help/comment text, and registration/`lib.rs` emission" or drop the specific region list and keep the re-locate-by-symbol instruction.

No other findings.
