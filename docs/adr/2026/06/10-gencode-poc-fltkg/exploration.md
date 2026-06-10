# Exploration: gencode-poc-fltkg TODO

Adversarial fact-check of the TODO claim against the code. No prescriptions.

---

## Makefile: what the target actually looks like

`Makefile:78-79` — `TODO(gencode-poc-fltkg)` comment is a Makefile comment above the `gencode:` target, not inside it.

`Makefile:99-103` — the actual one-liner (the TODO says "Makefile:83-88", which is wrong; lines 83-88 are Python fegen/bootstrap grammar generation steps unrelated to the PoC):

```makefile
uv run python -c "\
import sys; sys.path.insert(0, 'tests'); \
from test_gsm2tree_rs import _make_poc_grammar; \
from fltk.fegen.gsm2tree_rs import RustCstGenerator; \
open('src/cst_generated.rs', 'w').write(RustCstGenerator(_make_poc_grammar()).generate())"
```

The `gen-rust-cst` CLI path used for all other Rust targets is at `Makefile:105-108` (for `src/cst_fegen.rs`) and `Makefile:110` (fixture crate).

---

## The PoC grammar's GSM features vs. .fltkg syntax support

`_make_poc_grammar()` (`tests/test_gsm2tree_rs.py:29-96`) builds exactly two rules:

**`identifier` rule** (`test_gsm2tree_rs.py:36-51`):
- 1 item: `label='name'`, `disposition=INCLUDE`, `term=Regex('[_a-z][_a-z0-9]*')`, `quantifier=REQUIRED`
- `initial_sep=NO_WS`, `sep_after=[NO_WS]`

**`items` rule** (`test_gsm2tree_rs.py:53-91`):
- 4 items: literals `"."`, `","`, `":"` and rule-ref `identifier`, all `INCLUDE`/`REQUIRED`
- `initial_sep=NO_WS`, `sep_after=[NO_WS, WS_ALLOWED, WS_REQUIRED, NO_WS]`

All of these are expressible in `.fltkg` syntax (`fltk/fegen/fegen.fltkg`):
- `label:$term` syntax for labeled+INCLUDE items (`fegen.fltkg:11`: `item := ( label:identifier . ":" )? . disposition? . term . quantifier? , ;`)
- `.` / `,` / `:` separators between items (`fegen.fltkg:6-9`)
- `$/regex/` for included regex term
- `$"literal"` for included literal term
- No trivia rule in the .fltkg file — the auto-default trivia (whitespace: `[\s]+`) is added by `RustCstGenerator.__init__` via `gsm.add_trivia_rule_to_grammar` (`gsm2tree_rs.py:40`, `gsm.py:380-407`)

A valid `.fltkg` file for the PoC grammar:
```
identifier := name:$/[_a-z][_a-z0-9]*/ ;
items := no_ws:$"." . ws_allowed:$"," , ws_required:$":" : item:$identifier ;
```

This was verified to parse into a GSM that is field-for-field identical to `_make_poc_grammar()`'s output (both rules, all 5 items, all labels, dispositions, terms, quantifiers, separators).

---

## Would gen-rust-cst produce byte-identical output?

**Yes.** Both paths produce identical output at every layer:

1. **GSM equality**: `_read_and_parse_grammar('/tmp/poc_grammar2.fltkg')` returns a `gsm.Grammar` with rules `['identifier', 'items']` where every field (label, disposition, term, quantifier, sep_after, initial_sep) matches `_make_poc_grammar()` exactly.

2. **RustCstGenerator input**: `_parse_grammar_raw` (`genparser.py:254-261`) delegates to `_read_and_parse_grammar` without applying trivia processing — intentionally, because `RustCstGenerator.__init__` applies it internally (`gsm2tree_rs.py:40`). The one-liner also passes the raw grammar. Both paths reach `RustCstGenerator` with the same pre-trivia GSM.

3. **Generator output**: `gen1.generate() == gen2.generate()` — verified. The committed `src/cst_generated.rs` is byte-identical to the output of `gen-rust-cst` on the candidate `.fltkg`.

4. **Committed file**: `diff src/cst_generated.rs <(gen-rust-cst poc.fltkg -)` exits 0 — the committed file matches the `.fltkg` path today.

---

## The preamble-drift claim

The TODO says the `.fltkg` path would "pick up any future preamble changes automatically." This claim needs scrutiny.

The one-liner calls `RustCstGenerator(_make_poc_grammar()).generate()`, which calls `self._preamble()` (`gsm2tree_rs.py:229, 247`). The `gen-rust-cst` CLI calls `gsm2tree_rs.RustCstGenerator(grammar).generate()` (`genparser.py:318, 328`), which calls the **same** `_preamble()` method. There is no separate preamble path — both routes call `RustCstGenerator.generate()` → `_preamble()`.

**Conclusion**: the one-liner already picks up preamble changes from `gsm2tree_rs.py:_preamble()` at regeneration time. The preamble-drift claim in the TODO is inaccurate. The actual drift risk is that `_make_poc_grammar()` (a hand-built Python function) could diverge from the grammar's intended specification, while a `.fltkg` file would be a self-consistent declarative source.

---

## Is the one-liner a practical drift risk?

The one-liner has one coupling that a `.fltkg` would eliminate: it imports `_make_poc_grammar` from `tests/test_gsm2tree_rs.py`. If that function's GSM is changed (e.g., to add a rule or relabel an item), `src/cst_generated.rs` diverges from the previous committed file only when `make gencode` is re-run — the same latency as any other generated file. No automated guard prevents `_make_poc_grammar` from drifting away from whatever grammar `src/cst_generated.rs` is meant to represent.

`_make_poc_grammar` is also used directly by 8+ fixtures and test methods in `test_gsm2tree_rs.py` (lines 136, 485, 491, 498, 505, 749) for generator unit tests. These tests test the generator against the PoC grammar and would remain valid regardless of whether the Makefile uses the function or a `.fltkg` file.

---

## Blockers the TODO didn't mention

None found. The `.fltkg` format supports all GSM features used by the PoC grammar. The `gen-rust-cst` CLI path is operational and already used for `src/cst_fegen.rs` and the fixture crate. The `--protocol-module` / `--pyi-output` flags are optional; they are not needed for `src/cst_generated.rs` (no `.pyi` is currently generated for the PoC module).

One open question: if `_make_poc_grammar()` is kept in test code for the generator unit tests (which it must be — those tests need a programmatic grammar, not a file), the Makefile could either (a) parse the `.fltkg` file via CLI, or (b) keep the one-liner but point it at the `.fltkg` file instead. The `.fltkg` file would then be the single source of truth; the Python function in tests would either be deleted or verified to match the `.fltkg` via a test.

---

## Summary of verified facts

| Claim | Verified result |
|---|---|
| Makefile one-liner is at lines 83-88 | **False** — one-liner is at `Makefile:99-103`; lines 83-88 are fegen/bootstrap Python gen |
| PoC GSM features are all expressible in .fltkg | **True** — all items, dispositions, separators, labels supported |
| gen-rust-cst produces byte-identical output | **True** — diff exits 0 against committed `src/cst_generated.rs` |
| One-liner picks up preamble changes | **True** — both paths use same `RustCstGenerator.generate()` → `_preamble()` |
| Preamble drift is the actual risk | **False** — preamble is shared; real risk is `_make_poc_grammar()` specification drift |
| No .fltkg file exists for the PoC grammar | **True** — `find . -name "*.fltkg"` lists 6 files, none for the PoC |
| _make_poc_grammar is used outside gencode | **True** — used by 8+ test fixtures in `test_gsm2tree_rs.py` directly |
