# Design: single source of truth for generated Rust child-enum naming

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Pure refactor. Generated output must be byte-identical.
**Requirements:** `request.md` (this dir). **Exploration:** `exploration.md`, `exploration-str-lit-context.md` (this dir).

Line numbers below are as of this writing; if the module-split work (`docs/adr/2026/06/11-rust-bindings-module-split/`) lands first, re-locate by symbol name.

## Root cause / context

The `{ClassName}Child` enum-name convention is constructed independently at four sites (all verified in `exploration.md` and re-verified against current code):

1. `fltk/fegen/gsm2parser_rs.py:192-197` — `RustParserGenerator._child_enum_name`: `self._class_name(rule_name) + "Child"`. Carries the `TODO(rust-naming-shared)` comment. Callers: lines 550, 965.
2. `fltk/fegen/gsm2tree_rs.py:497` — `_child_enum_block`: `enum_name = f"{class_name}Child"`.
3. `fltk/fegen/gsm2tree_rs.py:621` — `_node_block`: `enum_name = f"{class_name}Child"`.
4. `fltk/fegen/gsm2tree_rs.py:1058` — `_label_type_info`: `enum_name = f"{self._py_gen.class_name_for_rule_node(rule_name)}Child"`.

No generation-time cross-check exists; a rename at one site without the others produces parser code referencing nonexistent CST enum names, detected only when `cargo` compiles the generated output.

The `Label` side is already single-source: `RustCstGenerator._label_enum_rust_name` (`gsm2tree_rs.py:399-406`) and `_label_enum_python_name` (`gsm2tree_rs.py:408-411`) are methods; `gsm2parser_rs.py` never constructs label enum names independently (it delegates via `self._cst._label_type_info`, `gsm2parser_rs.py:199-201`). The TODO.md text naming `_label_enum_rust_name` as a duplication site is wrong; only the `Child` suffix is duplicated.

Dependency direction is already correct for the fix: `gsm2parser_rs.py:23` imports `RustCstGenerator`; `gsm2parser_rs.py:82` holds `self._cst`; existing delegations at `_class_name` (line 188-190) and `_label_type_info` (line 199-201). No new imports, no cycle.

## Proposed approach

One new method, four call-site edits, TODO removal (TODO.md entry + code comment). No behavior change; the new method returns the exact string the four sites construct today, so output is byte-identical by construction.

### New method

On `RustCstGenerator` (`fltk/fegen/gsm2tree_rs.py`), adjacent to `_label_enum_rust_name` (the existing naming-helper section, "Label enum" block starting at line 395):

```python
@staticmethod
def child_enum_name(class_name: str) -> str:
    """Return the Rust child value enum name for a node class (single source of truth).

    Used by both this generator and RustParserGenerator (gsm2parser_rs.py); a rename
    here propagates to every emission site.
    """
    return f"{class_name}Child"
```

Decisions:

- **Parameter is `class_name`, not `rule_name`** — mirrors `_label_enum_rust_name(class_name)`; sites 2 and 3 already hold `class_name` and would otherwise re-derive it. Site 4 and the parser side already derive `class_name` one line away.
- **Public (no underscore)** — it is consumed cross-class by `RustParserGenerator`. The parser generator currently reaches into `self._cst._py_gen` and `self._cst._label_type_info` (private access); the new method should not add to that pattern. Cleaning up the two existing private-access points is out of scope (pure-refactor constraint: smallest change that single-sources the name).
- **`@staticmethod`** — matches `_label_enum_rust_name`; no instance state needed.

### Call-site edits

- `gsm2tree_rs.py:497` (`_child_enum_block`): `enum_name = self.child_enum_name(class_name)`.
- `gsm2tree_rs.py:621` (`_node_block`): `enum_name = self.child_enum_name(class_name)`.
- `gsm2tree_rs.py:1058` (`_label_type_info`): `enum_name = self.child_enum_name(self._py_gen.class_name_for_rule_node(rule_name))`.
- `gsm2parser_rs.py:192-197` (`_child_enum_name`): body becomes `return self._cst.child_enum_name(self._class_name(rule_name))`; delete the `TODO(rust-naming-shared)` comment. The wrapper stays (it owns the rule-name→class-name step) so its callers at lines 550 and 965 are untouched.

### Not changed

- `_label_enum_rust_name` / `_label_enum_python_name`: already single-source; renaming or publicizing them serves no consumer and adds churn.
- `_rust_str_lit`: explicitly out of scope per request.md (slug `rust-str-lit-shared` triaged Delete — bug unreachable under the `[_a-z][_a-z0-9]*` identifier constraint enforced by the grammar and `RustCstGenerator.__init__`; see `exploration-str-lit-context.md`). No shared utility module is created; `RustCstGenerator` is the home, per request.md fix shape.
- Doc comments mentioning `<Name>Child` (e.g. `gsm2tree_rs.py:489`, `:1044`, `:1049`): prose, not name construction; left alone.

### TODO bookkeeping

- Remove the `## rust-naming-shared` entry from `TODO.md` (currently lines 68-70).
- The `TODO(rust-naming-shared)` code comment is removed by the `gsm2parser_rs.py` edit above. These are the only two occurrences (verified by grep; `exploration-str-lit-context.md` §6 cites the same two locations).

### Sequencing with module-split

Per request.md, this rides along with or follows the module-split work. The module-split touches `RustCstGenerator.__init__` validation (`gsm2tree_rs.py:56-80`), pyi safety-comment text (`gsm2tree_rs.py:142-143`), a new TODO comment, registration/`lib.rs` emission (`gsm2parser_rs.py:813-923`, `gsm2tree_rs.py:1517-1531`), and the old TODO comment at `gsm2parser_rs.py:816-820` (per its design §2.10); this change touches naming helpers (`gsm2parser_rs.py:192-197`, `gsm2tree_rs.py:395-411`) and three enum-name assignments (497, 621, 1058) — disjoint regions, so conflicts are unlikely either way. Keep this as a separate commit. If module-split lands first and shifts lines, re-locate by symbol (`_child_enum_name`, `_child_enum_block`, `_node_block`, `_label_type_info`).

## Edge cases / failure modes

- **Accidental output change** — the only real risk in a pure naming refactor (typo in the helper, wrong variable passed at site 4). Caught by the byte-identical regen diff (below) and by `cargo` compilation of regenerated fixtures in the existing test flow.
- **Future drift** — the failure mode this refactor eliminates: after the change, the parser and CST generators converge by construction, so no generation-time consistency assertion is needed.
- No runtime, API, or generated-surface change; downstream-consumer compatibility (CLAUDE.md) is trivially preserved by byte-identical output.

## Test plan

No new tests: the convergence guarantee is structural (one definition), so a test asserting the two generators agree would be a tautology, and a grep-style "no inline `Child` f-string" guard would be brittle prose-vs-code matching.

Verification (per request.md):

1. `make gencode` — regenerates all Python and Rust outputs (Python CST/parser modules; `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fegen/src/{cst,parser}.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/{cst,parser}.rs`, spike copy) and normalizes formatting.
2. `git diff --exit-code` on generated files — must be empty (byte-identical). If module-split landed first, identical modulo that work's already-committed changes.
3. Existing generator unit tests: `fltk/fegen/test_gsm2parser_rs.py`, `tests/test_gsm2tree_rs.py`.
4. Full suite: `uv run --group dev maturin develop`, `uv run pytest`; `make fix`; `make check`.

## Open questions

None. Sequencing is user-decided; the method signature and home follow existing precedent in the same file.
