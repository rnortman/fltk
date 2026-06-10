# Deep correctness review — gencode-poc-fltkg

Commit reviewed: 815c95f (base 6d42885). Style: concise, precise, no padding.

Verified clean before findings:

- Regen path byte-identity: `gen-rust-cst fltk/fegen/test_data/poc_grammar.fltkg` → output `cmp`-identical to committed `src/cst_generated.rs`. Constraint "must not change by a single byte" holds.
- All three new tests pass as committed.
- Quantifier comparison is sound: `gsm.Quantifier` subclasses have identity-only `__eq__`, but `fltk2gsm.Cst2Gsm.visit_quantifier` returns the module singletons (`gsm.REQUIRED` etc., `fltk/fegen/fltk2gsm.py:125,153-160`), and `_make_poc_grammar` uses the same singletons — `==` works.
- Term comparison sound: `Literal`/`Regex`/`Identifier` are frozen dataclasses with field equality.
- No residual `gencode-poc-fltkg` references in tracked files at HEAD.
- Makefile invocation mirrors the `cst_fegen.rs` rule minus `--protocol-module`, matching the old one-liner's behavior (no `.pyi` emitted for PoC grammar).

## correctness-1: drift-guard fixture accepts a partial parse the real gen path rejects

- `tests/test_gsm2tree_rs.py:1187` (`fltkg_grammar` fixture, `assert result is not None`).
- The fixture docstring claims it parses "via the same raw pipeline used by gen-rust-cst", but the real pipeline (`_read_and_parse_grammar`, `fltk/fegen/genparser.py:50`) additionally requires `result.pos == len(terminals.terminals)`. The test fixture only checks `result is not None`. `apply__parse_grammar` returns a partial result when trailing content fails to parse.
- Empirically confirmed: appending `broken := @@@ ;` to the grammar source yields a non-None result at `pos=119` of `len=135`; `Cst2Gsm` produces a GSM containing only the two original rules, so all three drift tests pass unchanged.
- **Consequence**: the spec's verification criterion "drift-guard test fails if either grammar source is perturbed" (request.md §Verification) is violated for any perturbation that appends or trails unparsable content after the last valid rule. The drift tests stay green while `make gencode` hard-fails on the same file (genparser exits 1 on partial parse). Not silent output drift — gencode fails loudly — but the guard reports a false pass and diverges from the pipeline it claims to replicate.
- Fix: in the fixture, assert `result.pos == len(terminals.terminals)` (mirroring `genparser.py:50`) alongside the non-None check.

## correctness-2: `Items.initial_sep` not compared — GSM divergence passes the drift guard

- `tests/test_gsm2tree_rs.py:1201-1227` (`test_identifier_rule_items`, `test_items_rule_items`).
- The tests compare alternative count, item count, `sep_after`, and per-item `label`/`disposition`/`term`/`quantifier`. `gsm.Items` has a fifth compared field, `initial_sep` (`fltk/fegen/gsm.py:74`), settable from `.fltkg` source via a leading separator on an alternative (`fltk/fegen/fltk2gsm.py:62-66`).
- Empirically confirmed: changing the grammar line to `items := : no_ws:$"." ...` (leading `:`) parses fully and yields `initial_sep=WS_REQUIRED` while `_make_poc_grammar()` builds `NO_WS`; every field the test compares is identical, so all three drift tests pass despite the two GSMs being unequal.
- **Consequence**: the test's stated purpose — "the GSM parsed from the .fltkg file equals the GSM built by `_make_poc_grammar()`" (request.md §3) — is not fully enforced: the two sources of truth can silently diverge on `initial_sep`. Generated `src/cst_generated.rs` is currently unaffected (`gsm2tree_rs.py` reads neither `initial_sep` nor `sep_after`), but the guard exists precisely to catch GSM-level divergence before it matters; if the Rust generator ever starts consuming separators (it already gets the full GSM), this divergence becomes output drift with no failing test.
- Fix: add `assert fltkg_alt.initial_sep == expected_alt.initial_sep` in both per-rule tests. (Optional hardening: `assert fltkg_alt == expected_alt` for `Items` would cover all compared dataclass fields at once — `sep_after` and `initial_sep` are enums, items are dataclasses, and quantifiers are shared singletons, so dataclass equality holds for this grammar; but the explicit per-field asserts give better failure messages, so adding the one missing field is the minimal fix.)

No other findings. Off-by-one, operator, variable, control-flow, and resource checks over the Makefile and test diff came up clean; `Rule.is_trivia_rule` is uncompared but cannot diverge through the raw (pre-trivia) pipeline for these rule names.
