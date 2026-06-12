# Deep-correctness review — rust-generated-ident-collisions

Style: concise, precise, no padding. Audience: smart LLM/human.

Reviewed: `d2abc80..4f66083` (HEAD 4f66083). Files: `fltk/fegen/gsm2tree_rs.py`, `tests/test_gsm2tree_rs.py`.

Verified clean: trivia-annotation keying (`gsm.TRIVIA_RULE_NAME not in grammar.identifiers` exactly mirrors `add_trivia_rule_to_grammar`'s no-op condition, `gsm.py:425`); emitted-only `{CN}Label` claiming matches `_label_enum_block`'s emission condition (`model.labels` ↔ `_rule_info` labels); `rule_models` is populated for every rule in `CstGenerator.__init__` (`gsm2tree.py:43-44`) so `.get()` never silently drops a labeled rule; non-injective CN handling (`snake_to_upper_camel` collapses `__`, `naming.py`); per-rule reserved-name precedence over the cross-rule check; within-rule family names cannot self-collide (fixed affixes, including degenerate CNs `""`/`"Py"`); Python-visible pyclass names (`{CN}`, `{CN}_Label`) cannot collide unless the Rust names already do (CN contains no `_`). New tests pass; the emitted-only positive test's `pub enum FooLabel {`-with-brace assertion correctly avoids the `FooLabelLabel` substring trap.

## correctness-1

- **File:line**: `fltk/fegen/gsm2tree_rs.py:39-45` (`_RESERVED_CLASS_NAMES`, at HEAD 4f66083).
- **What's wrong**: The change adds `DropWorklistItem` to the reserved set but omits `EqWorklistItem`, which is emitted under identical conditions: `_eq_block` (gsm2tree_rs.py:2137 at HEAD, `enum EqWorklistItem {`) emits a module-level enum whenever the child-class union is non-empty, exactly parallel to `_drop_block`'s `DropWorklistItem`.
- **Why**: The design's root-cause survey ("That set also misses `DropWorklistItem`") caught only one of the two worklist enums introduced by d2abc80 (`rust-cst-eq-depth`), which added `EqWorklistItem` in the same emission pattern. The cross-rule claims check cannot catch it either: it only claims the `CN`/`Py{CN}`/`{CN}Child`/`{CN}Label` families, and `EqWorklistItem` matches none of the assert invariant's patterns (no `Py` prefix, no `Child`/`Label` suffix), so by the module comment's own rule it must be in the reserved set.
- **Consequence**: A grammar containing a rule named `eq_worklist_item` (or any rule whose CN is `EqWorklistItem`, e.g. `eq__worklist_item`) plus at least one node-typed child anywhere generates two `EqWorklistItem` definitions in one module → rustc E0428 with no pointer to the grammar — precisely the failure mode this change exists to convert into a generation-time `ValueError`.
- **Fix**: Add `"EqWorklistItem": "the generated EqWorklistItem eq-worklist enum"` to `_RESERVED_CLASS_NAMES` and extend the reserved-name test parametrize.
- **Status note**: The uncommitted working tree (post-HEAD, concurrent fix pass) already contains exactly this fix (reserved entry + `("eq_worklist_item", "EqWorklistItem", "EqWorklistItem")` test param); empirically verified rejected there. Ensure it lands in a commit — at HEAD the gap is real.

## correctness-2

- **File:line**: `fltk/fegen/gsm2tree_rs.py:50-53` (module-level `assert`).
- **What's wrong**: The Py/Child/Label invariant guard is a bare `assert`, but the comment (lines 47-49) and the cross-rule check's correctness argument describe it as "machine-checked at module load". `assert` statements are compiled out under `python -O` / `PYTHONOPTIMIZE`.
- **Why**: The decision *not* to seed reserved names into the claims dict is justified entirely by this invariant. Under `-O` the invariant is never evaluated, so the justification holds only by convention, not by machine check.
- **Consequence**: If a future reserved name violates the invariant (e.g. `"PySpan"`), an optimized-mode run imports cleanly and a rule deriving `Py{CN} == "PySpan"` is accepted, producing duplicate-identifier Rust output (E0428) with no generation-time diagnostic — the coverage gap the assert exists to make impossible. Low likelihood (dev/test runs are unoptimized, so the violation would normally be caught in CI), but the mechanism does not match its stated guarantee.
- **Fix**: Replace with an explicit `if any(...): raise AssertionError(...)` (or move the check into `RustCstGenerator.__init__`'s validation path) so it survives `-O`.

## correctness-3 (pre-existing; adjacent, not introduced by this diff)

- **File:line**: `fltk/fegen/gsm2tree_rs.py:18` (`_IDENTIFIER_RE`) interacting with the new claims loop at 131-144.
- **What's wrong**: `^[_a-z][_a-z0-9]*$` admits underscore-only rule names (`_`, `__`), which `snake_to_upper_camel` collapses to the empty string (documented contract, `naming.py`). CN `""` flows through both the reserved check (no match) and the new claims check (claims `""`, `"Py"`, `"Child"`, `"Label"`).
- **Consequence**: A single underscore-only rule is accepted and emits `pub struct  {` — a Rust syntax error with no grammar-level diagnostic (same uncompilable-output class this change targets, different identifier family). Two underscore-only rules collide on the empty identifier and the new message reads `Generated Rust identifier '' collides: ...` — technically correct claimant info, but the empty quoted identifier is mystifying. Also `_`'s derived `"Child"`/`"Label"`/`"Py"` claims can collide with real rules named `child`/`label`/`py`, producing messages that are accurate but hard to decode.
- **Fix (follow-up, not this change)**: Reject rule names whose CN is empty (or tighten `_IDENTIFIER_RE` to require at least one `[a-z0-9]`). Worth a `TODO(slug)` if not done now.

No other logic, control-flow, or data-flow defects found in the committed range.
