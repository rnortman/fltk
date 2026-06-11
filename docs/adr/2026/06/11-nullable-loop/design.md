# Design: nullable-repetition infinite-loop guard + validator gap fix

Concise. Precise. Complete. Unambiguous. No padding. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir). This design does not restate them; it cites them.

## 1. Root cause / context

Two defects, confirmed empirically during design (not theory — per user direction in `request.md`):

1. **Validator gap** (`gsm.py:108-111`): `Item.can_be_nil` returns `self.quantifier.is_optional()`, ignoring the term. A REQUIRED-quantifier item with a nullable term (e.g. `Regex(r"a*")`, `Literal("")`, or a nil-able rule reference) is reported non-nil. `Items.can_be_nil` (`gsm.py:77-98`) therefore under-reports, so `validate_no_repeated_nil_items` (`gsm.py:340-356`) accepts a repeated sub-expression whose inner item is required-but-nullable. Exploration §3.

2. **No loop progress guard** in either backend's repetition codegen:
   - Rust: `gsm2parser_rs.py:674-694` (`_gen_item_multiple`) — `while let Some(one_result) = {...} { pos = one_result.pos; ... }`. `TODO(nullable-loop)` comment at 669-673.
   - Python: `gsm2parser.py:555-604` (`gen_item_parser_multiple`) — IIR `while_` loop, first body statement `pos = one_result.pos`.

   Both backends have a post-loop `pos == span_start` failure check for `+` (Rust 695-698, Python 581-585), but it is unreachable when the loop never exits.

**Empirical confirmation** (design-stage, current code): trigger grammar `rule := (r"a*" .)+` built as GSM objects — outer item ONE_OR_MORE over a sub-expression whose single inner item is REQUIRED with term `Regex(r"a*")`:
- `validate_no_repeated_nil_items` passes it (gap confirmed).
- `generate_parser` (Python backend) succeeds; parsing `"aab"` hangs (confirmed via 5s alarm: iteration 1 consumes `"aa"`, iteration 2 matches empty at pos 2 forever).

The Rust backend emits the structurally identical loop from the same GSM input, so the same grammar is expected to hang it; §5.1 demonstrates this end-to-end (with the request's stop-and-escalate path if it unexpectedly does not).

Also confirmed at design time: **all eight in-tree `.fltkg` grammars** (fegen, bootstrap, fltk, toy, unparsefmt, poc_grammar, phase4_roundtrip, rust_parser_fixture) pass validation with the term-aware fix applied — the tightening rejects no currently-working grammar in this repo.

## 2. Proposed changes

### 2.1 Validator: term-aware `Item.can_be_nil` (root fix)

`fltk/fegen/gsm.py:108-111`:

```python
def can_be_nil(self, grammar: "Grammar") -> bool:
    """Check if this item can match empty: optional quantifier, or nullable term."""
    return self.quantifier.is_optional() or term_can_be_nil(self.term, grammar)
```

(`term_can_be_nil` is defined later in the module; fine at call time. Remove the now-stale `# noqa: ARG002`.)

This single change makes the entire nullability computation term-aware, because `Items.can_be_nil` → `Item.can_be_nil`, `Rule.can_be_nil` → `Items.can_be_nil`, and `term_can_be_nil` → `Items.can_be_nil` for sub-expressions. Consequences:

- `validate_no_repeated_nil_items` now rejects the trigger grammar (and the Identifier / empty-literal variants).
- `validate_trivia_rule_not_nil` (`gsm.py:328-337`) also tightens: a trivia rule like `_trivia := content:r"\s*"` (REQUIRED quantifier, nullable regex) is now rejected. This is a correct additional tightening — such trivia rules already violate the validator's stated invariant; only the detection was broken.

Tightening is monotone: the new predicate is `old OR term_nil`, so `can_be_nil` can only flip False→True. Validators can only newly *reject*; no previously-rejected grammar becomes accepted. Recursion terminates: rule-reference cycles are guarded by `Rule._computing_nil` (`gsm.py:39-40`); sub-expression nesting is finite.

A dedicated deep check inside the validator (request §Fix-shape option b) was considered and rejected: it would duplicate the nullability walk while leaving `Item.can_be_nil` returning wrong answers to every other caller.

### 2.2 Rust backend: per-iteration progress guard

`fltk/fegen/gsm2parser_rs.py`, `_gen_item_multiple`: emit the guard as the **first** loop-body line, before the `pos = one_result.pos;` assignment (placement is load-bearing — after the assignment the comparison is vacuously true; exploration §5):

```python
lines.append("        while let Some(one_result) = {")
lines.append(f"            {consume_expr}")
lines.append("        } {")
lines.append("            if one_result.pos == pos { break; }")   # NEW
lines.append("            pos = one_result.pos;")
```

Delete the `TODO(nullable-loop)` comment block (lines 669-673); replace with a short comment explaining the guard (zero-progress iteration → break; empty match discarded).

### 2.3 Python backend: identical guard via IIR `break`

`iir.Break` exists (`fltk/iir/model.py:707-709`) and the Python compiler already lowers it (`fltk/iir/py/compiler.py:218-220` → `ast.Break()`). Only the builder helper is missing.

**`fltk/iir/model.py`** — add to `Block`, alongside `return_`:

```python
def break_(self) -> "Break":
    self.body.append(brk := Break(parent_block=self))
    return brk
```

**`fltk/fegen/gsm2parser.py`**, `gen_item_parser_multiple` — insert before the existing `loop.block.assign(...)` (currently line 564):

```python
one_result_ref = loop.block.get_leaf_scope().lookup_as("one_result", iir.Var)
loop.block.if_(
    condition=iir.Equals(lhs=one_result_ref.load().fld.pos.load(), rhs=result.get_param("pos").load()),
).block.break_()
```

Compiles to `if (one_result.pos) == (pos): break` (`compile_expr`: `Load` unwraps, `FieldAccess` is `MemberAccess`, `Equals` is `BinOp`). Generated Python loop becomes (bare-truthiness walrus condition — `compile_while`, `compiler.py:277-282`, emits `({var} := {expr})`, not `is not None`; cf. committed `fltk_parser.py:134`):

```python
while one_result := <consume>:
    if one_result.pos == pos:
        break
    pos = one_result.pos
    <append>
```

Semantics identical to Rust: break before assignment **and before append** — a zero-width match is discarded, never added to the CST. Comparison is `==` in both backends (`one_result.pos < pos` is impossible: consume helpers and apply-wrappers return span ends ≥ input pos).

### 2.4 Resulting behavior at the guard

- Term always advances (every grammar the tightened validator accepts): guard never fires; parse results byte-identical to today. Request constraint "no change for currently-valid grammars" holds by construction.
- Empty match on iteration 1 with `+`: break, then existing post-loop `pos == span_start` check returns failure. Both backends.
- Empty match after k productive iterations: break; repetition succeeds with the k accumulated children and `pos` at the end of iteration k. Both backends. For `"aab"` against the trigger grammar: rule-level `apply__parse_rule(0)` returns ApplyResult pos=2 (iteration 1 consumed `"aa"`; the empty iteration-2 match is discarded). A full-input check (`parse_text`-style `pos == len`) then reports a partial-parse failure — so guard tests assert via `apply__parse_rule` directly.
- `*` quantifier: same, minus the post-loop check; zero productive iterations yield an empty success at the start pos (unchanged from today's behavior for non-matching terms).

### 2.5 Regeneration + TODO bookkeeping

- Regenerate all committed generated artifacts (`make gencode`), then `make fix` — every `+`/`*` loop in every regenerated parser gains one guard line. The `make gencode` output set is authoritative (Makefile:148-180); it includes `fltk_parser.py`, `fltk_trivia_parser.py`, `bootstrap_parser.py`, `bootstrap_trivia_parser.py`, `toy_parser.py`, `toy_trivia_parser.py`, `unparsefmt_parser.py`, `unparsefmt_trivia_parser.py`, fixture `parser.rs`, and fegen `parser.rs`. No public-API surface changes: no renames, no annotation changes; out-of-tree consumers see only the regen diff in their own regenerated parsers.
- Remove `nullable-loop` from `TODO.md` (the `TODO(nullable-loop)` code comment is deleted in §2.2).

## 3. Behavior changes (deliberate, called out per request §Constraints)

1. Grammars with repeated nullable terms that previously passed validation and hung at parse time are now **rejected at grammar-validation time** (`ValueError` from `validate_no_repeated_nil_items` via `classify_trivia_rules`, hit by both generator entry points: `gsm2parser.py:33` and `gsm2tree_rs.py:48` via `RustParserGenerator.__init__`).
2. Trivia rules whose nullability was masked by the quantifier-only check are now rejected by `validate_trivia_rule_not_nil`.
3. For grammars reaching the generators with validation bypassed (direct `gsm.Grammar` construction paths — the reason the guard exists as defense-in-depth), parse behavior changes from *hang* to *terminate with the empty match discarded*. Identical in both backends.

No parse-result change for any grammar that is accepted and terminates today: the guard fires only on zero-progress iterations, which such grammars cannot produce.

## 4. Edge cases / failure modes

- **Guard placement bug** (break after `pos` update → breaks every iteration): prevented by behavioral tests asserting multi-iteration parses still consume full input (existing parity corpus, e.g. `("items", "123", SUCCESS)`), plus the new partial-progress test (§5, `"aab"` → pos 2 requires iteration 1 to complete normally).
- **Discarded side effects on the empty iteration**: a zero-progress sub-expression iteration may have allocated a node; break discards it before append in both backends — no CST divergence.
- **Memoized consume path**: Identifier terms go through `apply__*` memoization and return the same empty result each iteration; guard handles identically.
- **`classify_trivia_rules` early-returns when `_trivia` is absent** (`gsm.py:278-280`), skipping all validation. Both generator paths ensure `_trivia` exists before classification (`generate_parser` calls `add_trivia_rule_to_grammar` first; `gsm2tree_rs.py:48` likewise; bare `ParserGenerator` raises at `gsm2parser.py:87-89` if `_trivia` missing). Residual bypass via direct construction is exactly what the loop guard covers.
- **Invalid regex in `Regex.can_be_nil`**: returns False conservatively (`gsm.py:147-154`) — under-approximation; such grammars fail later at regex compile, not via a hang (the guard still protects).
- **Memoization fields** (`Items._can_be_nil`, `Rule._can_be_nil`, `Regex._can_be_nil`): per-object caches; the term-aware result is computed once per object as before. Pre-existing pattern, unchanged.
- **Existing tests encode the bug**: `fltk/fegen/test_nil_validation.py:168-206` asserts "Required item (never nil regardless of term)" with `Literal("")` — these assertions flip under the fix and must be updated (they document the gap, not a contract).

## 5. Test plan (TDD order: all new tests written first, failing against current code)

New file `tests/test_nullable_loop_guard.py` for guard-level tests; validator tests extend `fltk/fegen/test_nil_validation.py`. Shared trigger-grammar builders live in the new test file (or a small helper importable by the subprocess scripts).

### 5.1 Failing-first: hang demonstration (request's mandatory first step)

- **Python backend hang/guard test.** Subprocess script (precedent: `tests/test_rust_span.py::_run_script`): child process no-ops `gsm.validate_no_repeated_nil_items` (monkeypatch in-child — bypasses the §2.1 validator so the guard layer is tested in isolation), builds the trigger grammar, runs `generate_parser`, calls `apply__parse_rule(0)` on `"aab"` and `"b"`, prints outcomes. Parent runs with `subprocess` timeout (~30s, generous for generation); `TimeoutExpired` → kill → `pytest.fail("Python backend hung on nullable repetition")`. Pre-fix: times out (confirmed in §1). Post-fix expected: `"aab"` → ApplyResult pos=2; `"b"` → None (`+` post-loop check).
- **Rust backend hang/guard test.** Same trigger grammar; in-process generation with validator monkeypatched: `RustParserGenerator(grammar).generate()` → `parser.rs`, `RustCstGenerator` output → `cst.rs`. Write a minimal binary crate in `tmp_path`: `Cargo.toml` with path deps on the in-repo `fltk-parser-core` and `fltk-cst-core` crates — the latter declared `fltk-cst-core = { path = ..., default-features = false }`, since its `python` feature is default-on (`crates/fltk-cst-core/Cargo.toml: default = ["python"]`) and merely not enabling it still links pyo3; precedent: fltk-parser-core's own dep declaration. `fltk-parser-core` has no `python` feature at all (never links pyo3). `main.rs` declaring `mod cst; mod parser;` and printing the `apply__parse_rule(0)` outcome for `"aab"` and `"b"`. `cargo build` first (long timeout; builds can't hang), then run the binary with a short timeout (~10s). Timeout → `pytest.fail("Rust backend hung...")`. The Rust hang is inferred from the structurally identical emitted loop (§1); this test is its empirical demonstration — per the user direction in `request.md`, if it unexpectedly does *not* hang pre-fix, stop and escalate instead of proceeding on theory. Skip with explicit reason if `cargo` is not on PATH (toolchain is a documented repo requirement; mirrors the importorskip pattern with its "all-skipped is a failure signal" note). Cost: one small debug cargo build per test session — accepted; this is the only way to demonstrate the actual generated Rust parser hanging/terminating, which the user direction mandates.
- **Cross-backend parity of guard results**: assert the two tests' outcomes match (pos=2 / fail on the same inputs).

If hang cannot be induced, ESCALATE for review of whether this is necessary at all.

### 5.2 Failing-first: validator gap

In `fltk/fegen/test_nil_validation.py`:
- `validate_no_repeated_nil_items` raises `ValueError` for: trigger grammar (REQUIRED `Regex(r"a*")` in repeated sub-expression); variant with `Literal("")`; variant with a REQUIRED Identifier referencing a nil-able rule. All currently pass validation → tests fail pre-fix.
- Term-aware `Item.can_be_nil` unit cases: REQUIRED + nullable regex → True; REQUIRED + `Literal("")` → True; REQUIRED + nil-able rule ref → True; REQUIRED + non-nullable term → False; optional quantifiers → True regardless.
- Update the flipped assertions in `test_item_nil_detection_with_quantifiers` (§4 last bullet).

### 5.3 Generator-level rejection (validation wired into both entry points)

- `generate_parser(trigger_grammar)` raises `ValueError` (match "Repeated potentially-nil").
- `RustParserGenerator(trigger_grammar)` raises `ValueError` at construction.

### 5.4 Emitted-source guard placement (cheap regression net; always runs, even where 5.1's cargo test skips)

- Rust: generated `parser.rs` text for a simple `+` grammar contains `if one_result.pos == pos { break; }` immediately after the `} {` loop opener and before `pos = one_result.pos;` (style precedent: `tests/test_gsm2tree_rs.py` source-text assertions).
- Python: `ast.unparse` of the compiled parser module for the same grammar contains the `if one_result.pos == pos:`/`break` sequence before the `pos = one_result.pos` assignment.

### 5.5 No-regression

- Full suite both backends: `uv run pytest`, `cargo test` (workspace + fixture crates), parity corpora (`test_rust_parser_parity_fegen.py`, `test_rust_parser_parity_fixture.py`) unchanged.
- `make gencode` regen + `make fix`; committed generated code clean under `make check`.
- §1's design-stage check (all in-tree grammars pass tightened validation) becomes implicit in the above: regen would fail otherwise.

## 6. Open questions

None. The one judgment call — accepting a test-time `cargo build` for the Rust hang demonstration — is mandated by the user direction ("construct a grammar that tricks the current parsers", both backends); the cheap textual check (§5.4) covers cargo-less environments.
