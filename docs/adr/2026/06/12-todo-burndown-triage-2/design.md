# Design: reject underscore-only rule names and labels (`TODO(empty-cn-underscore-rule)`)

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Requirements: user-supplied direction in the task (no separate requirements doc). Scope: reject
underscore-only rule names AND labels at generation time with a clear diagnostic; do not change
behavior for currently-valid grammars except as explicitly called out below; small change.

Exploration inputs (read these for full evidence):
- `exploration-empty-cn-underscore-rule.md` (same directory)
- `exploration-underscore-rule-name-reachability.md` (same directory)

## Root cause

`naming.snake_to_upper_camel` (`fltk/fegen/naming.py:22`) maps every underscore-only name
(`_`, `__`, ..., and `""`) to the empty string. Derived class names (CN), enum variant names, and
NodeKind member names are built from that result, and **no layer validates that the result is
non-empty**:

- Grammar regex (`fegen.fltkg:16`: `/[_a-z][_a-z0-9]*/`) admits `_` and `__`.
- `fltk2gsm.Cst2Gsm.visit_rule` / `visit_item` (`fltk/fegen/fltk2gsm.py:18-22,108-128`) do no name
  validation.
- No `gsm.validate_*` function inspects names (`fltk/fegen/gsm.py:344-419`).
- Python backend: crashes with `IndentationError: unexpected indent` from
  `pygen.stmt(" = enum.auto()")` (`gsm2tree.py:139` → `pygen.py:50`) — cryptic, no rule named.
- Rust backend: `RustCstGenerator.__init__` passes (`_IDENTIFIER_RE` at `gsm2tree_rs.py:22` matches
  `_`; CN `""` is in neither `_RESERVED_CLASS_NAMES` nor a cross-rule collision for a single such
  rule); `generate()` then emits `pub struct  {` — **silently malformed Rust** for INCLUDE rules.
- Labels: `_rust_variant_name("_") = ""` → empty Rust enum variant (syntax error). Empirically
  verified: a label `_` (top-level or nested in a parenthesized sub-expression) flows into the
  rule's model and generates `Label._` / `child__()` on the Python backend, and an empty variant on
  the Rust backend.

## Decision: single GSM-layer validation (for user review)

**Recommendation: one validator in `fltk/fegen/gsm.py`, invoked from `classify_trivia_rules`.**
Not per-backend checks.

Rationale:

1. **`classify_trivia_rules` is the universal chokepoint.** Every generation entry point flows
   through it:
   - `plumbing.generate_parser` (`fltk/plumbing.py:239`) — Python parser/CST pipeline
   - `plumbing.generate_unparser` (`fltk/plumbing.py:410`) — unparser pipeline
   - `genparser.parse_grammar_file` (`fltk/fegen/genparser.py:69`) — `generate` CLI
   - `gsm2parser.ParserGenerator.__init__` (`fltk/fegen/gsm2parser.py:33`) — direct Python parser gen
   - `gsm2tree_rs.RustCstGenerator.__init__` (`fltk/fegen/gsm2tree_rs.py:84`) — covers
     `gen-rust-cst` and `gen-rust-parser` CLIs (`RustParserGenerator` delegates to it)

   One check covers Python, Rust, and unparser backends with zero backend-code changes.
2. **Per-backend validation is the failure mode that produced this bug.** The Rust backend grew
   `_IDENTIFIER_RE`/reserved-name/collision checks the Python backend lacks; the Python backend
   dies with an unrelated-looking `IndentationError`. Duplicated checks drift.
3. **Established convention.** Three `validate_*` functions already run from
   `classify_trivia_rules` (`gsm.py:313-315`); this adds a fourth, and also catches
   programmatically constructed GSM grammars, which a `fltk2gsm`-layer check would miss.

**`_foo` / `_trivia` safety — confirmed.** The predicate is "derived name is empty"
(`naming.snake_to_upper_camel(name) == ""`), which fires only for names with zero `[a-z0-9]`
characters. `_trivia` → `Trivia`, `_foo` → `Foo`: both pass. Empirically verified end-to-end that
a grammar with rule `_foo` referenced from another rule still generates and parses.

**Deliberate behavior change (labels only) — flagging for explicit user sign-off.** Rule names: no
currently-valid grammar is affected — every backend already fails for rule `_`/`__` (Python:
`IndentationError`; Rust: `RuntimeError` or malformed output). Labels: a label `_` **currently
works end-to-end on the Python backend** (empirically verified: generates `Label._`, `child__()`,
`maybe__()`, parses fine). Rejecting it is a breaking change for any out-of-tree Python-backend
consumer using an underscore-only label. Justification: (a) the user direction explicitly extends
scope to labels; (b) the same grammar emits malformed Rust, so it violates the cross-backend
near-drop-in equivalence goal (CLAUDE.md); (c) the Python API it produces (`child__`, `append__`,
`extend__`) is degenerate. This is the one intentional rejection of a previously-Python-workable
construct.

## Proposed approach

### 1. New validator in `fltk/fegen/gsm.py`

```python
def validate_no_underscore_only_names(grammar: Grammar) -> None
```

- Import `fltk.fegen.naming` into `gsm.py` (leaf module, no FLTK imports — no cycle). Using
  `snake_to_upper_camel(name) == ""` as the predicate keeps the check definitionally in sync with
  name derivation (also rejects empty-string names from programmatic GSM construction).
- Walk every rule (including trivia rules): check `rule.name`; then walk
  `rule.alternatives → items → item.label` (skip `None`), **recursing into sub-expression terms**
  (`isinstance(item.term, Sequence)` → recurse into each `Items`, same pattern as
  `_collect_repeated_nil_errors` at `gsm.py:356-375`). Nested labels propagate into rule models
  (empirically confirmed), so they must be checked.
- Collect all violations; raise one `ValueError` listing them (matches
  `validate_no_repeated_nil_items`). Message names the offender and the cause, e.g.:
  - `Rule name '_' consists only of underscores; generated type names are derived by removing underscores, which would produce an empty name. Rename the rule (names like '_foo' are fine).`
  - `Label '_' in rule 'x' consists only of underscores; ...` (same shape).

### 2. Invoke from `classify_trivia_rules` (`gsm.py:289`)

Call `validate_no_underscore_only_names(grammar)` **first, before the
`if not trivia_rule: return grammar` early return** at `gsm.py:294-296`. The existing three
validators only run when `_trivia` exists; name validity is trivia-independent and must not be
skipped for trivia-less grammars.

### 3. No backend changes

- `_IDENTIFIER_RE` and `fegen.fltkg:16` stay as-is. Tightening the grammar regex would change
  parse-time identifier acceptance everywhere and require regenerating committed parsers — larger
  blast radius than needed; the GSM validator rejects the same grammars with a better message.
- The Rust backend's existing checks (`gsm2tree_rs.py:96-164`) remain as injection-safety /
  collision defense. Since `RustCstGenerator.__init__` calls `classify_trivia_rules` itself
  (line 84, before its own loops), the new validator fires first with the friendly diagnostic.
- Pre-existing gap noted, out of scope: the Rust backend's per-label `_IDENTIFIER_RE` /
  `_RESERVED_LABELS` loop (`gsm2tree_rs.py:105-121`) does not recurse into nested sub-expression
  items. The new validator covers the empty-CN slice of that gap; the rest is untouched.

### 4. Bookkeeping

- Delete the `TODO(empty-cn-underscore-rule)` comment at `gsm2tree_rs.py:18-21` and the `TODO.md`
  entry.
- Update the `_IDENTIFIER_RE` comment to note underscore-only names are rejected upstream by
  `gsm.validate_no_underscore_only_names`.

## Edge cases / failure modes

- **Grammar without `_trivia`**: validator runs before the early return — still enforced.
- **Two underscore-only rules** (`_` and `__`): both reported by the new validator (with both
  names) before the Rust cross-rule collision check would have fired on CN `""`.
- **Identifier term referencing rule `_`**: `fltk2gsm.visit_item` (`fltk2gsm.py:114-115`)
  auto-derives label `_` from the rule name. Rule-name rejection covers the defined-rule case; the
  label check covers a dangling reference to an undefined `_`.
- **Empty-string name from programmatic GSM**: same predicate rejects (`"" → ""`).
- **`_trivia`, `_foo`, `foo_`, `a__b` style names**: all derive non-empty CNs; unaffected. The
  auto-added trivia rule (label `content`) passes trivially.
- **Bypass**: constructing `gsm2tree.CstGenerator` directly and calling `gen_py_module()` without
  ever running `classify_trivia_rules` skips the check and keeps today's `IndentationError`. Every
  documented pipeline (plumbing, genparser CLI, both parser generators) is covered; accepted
  limitation, keeps the change single-point.

## Test plan (TDD — write first, confirm failing, then implement)

New file `fltk/fegen/test_name_validation.py` (placement mirrors
`fltk/fegen/test_nil_validation.py`, the existing GSM-validator test home).

Failing-first tests:

1. Rule named `_`: `plumbing.generate_parser(parse_grammar("_ := val:/[a-z]+/ ;"))` raises
   `ValueError` whose message contains `'_'` and "underscore". (Currently: `IndentationError`.)
2. Rule named `__`: same shape. (Currently: `IndentationError`.)
3. Top-level label `_`: grammar `x := _:/[a-z]+/ ;` raises `ValueError` naming rule `x` and
   label `_`. (Currently: generates successfully.)
4. Nested label `_`: grammar `x := (a:/[a-z]+/ | _:/[0-9]+/) ;` raises `ValueError`.
   (Currently: generates successfully.)
5. Rust path: `RustCstGenerator(grammar)` for a grammar with rule `_` raises `ValueError` with the
   friendly message at `__init__`. (Currently: `__init__` succeeds silently.)
6. Unit: for a programmatically built `Grammar` **without** `_trivia` containing rule `_`, both
   `gsm.validate_no_underscore_only_names(grammar)` and `gsm.classify_trivia_rules(grammar)` raise
   `ValueError` — the second assertion locks the before-early-return placement.
7. Multiple violations (rule `_` plus label `__` in another rule) reported in one `ValueError`.

Regression guards (must pass before and after):

8. Rule `_foo` referenced from another rule: `generate_parser` + `parse_text` succeed.
9. Label `_foo`, and a `capture_trivia=True` pipeline run (exercising the auto-added `_trivia`
   rule through the validator): both succeed.
10. Full suite stays green (fegen self-hosting grammar exercises `_trivia` throughout).

## Open questions

None. The single decision requiring user judgment — GSM-layer vs per-backend, plus the deliberate
label-`_` rejection on the Python backend — is presented above with the recommendation.
