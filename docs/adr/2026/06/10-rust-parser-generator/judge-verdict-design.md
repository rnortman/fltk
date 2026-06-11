# Judge verdict — design review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: design. Doc: `docs/adr/2026/06/10-rust-parser-generator/design.md`. Round 1.
Notes: `notes-design-design-reviewer.md` — 3 findings. Dispositions: `dispositions-design.md`.

## Findings walk

### design-1 — Fixed
Claim: §2.2 specified a header naming the grammar file, but the §2.1 constructor carried no filename parameter; consequence is an implementer forced to either silently drop the filename (ambiguating §4.1's structural-text assertions) or invent an unplanned constructor parameter.
Doc inspection: §2.1 signature now reads `__init__(self, grammar: gsm.Grammar, cst_mod_path: str = "super::cst", source_name: str | None = None)`. §2.2 item 1 specifies: "`source_name` is the constructor parameter (§2.1); the CLI passes the grammar file name. When `None`, the 'from `<source_name>`' clause is omitted (unit tests constructing from in-memory GSM need no fake filename)."
Assessment: fix matches the reviewer's suggested remedy exactly; the parameter is plumbed (constructor → header → CLI in §2.5's grammar-path argument) and the `None` case is specified, so §4.1 assertions are unambiguous in both unit-test and CLI contexts. Accept.

### design-2 — Fixed
Claim: fixed `use` block (§2.2 item 1) contradicted conditional regex-table emission (§2.2 item 2) — a reachable zero-regex grammar (custom literal-only `_trivia`, gsm.py:380-401; `\s+` enters only via trivia-rule separators, gsm2parser.py:641-650) leaves `OnceLock` and `Regex` imports unused, failing the §2.7 `-D warnings` lanes via `unused_imports` — violating the design's own clippy-clean invariant.
Doc inspection: §2.2 item 2 now reads: "The corresponding imports are conditional under the same predicate: `use std::sync::OnceLock;` and `use fltk_parser_core::regex::Regex;` are emitted only with the regex table (otherwise `unused_imports` fails the same lanes); every other import in the §item-1 block is used unconditionally. The zero-regex case is reachable: ..." with both source citations recorded.
Assessment: the conditional-emission predicate now covers exactly the two imports the table consumes. Checked the "every other import is used unconditionally" claim against the §2.2 anatomy: `Shared`/`Span`/`SourceText` (struct fields, constructors, alternative bodies), `ApplyResult`/`Cache`/`ErrorTracker`/`PackratState`/`TerminalSource` (Parser struct and `apply` wiring), `cst` (node types) — all used regardless of regex/literal presence, including the zero-literal case (omitted `consume_literal` uses only `ApplyResult`/`Span`, which alternative bodies use anyway). Holds. Accept.

### design-3 — Fixed
Claim: blanket "out-of-range/negative `pos` returns `None`" (§3, §4.3) is false for nullable rules — `min == ZERO` emits no progress check (gsm2parser.py:581-585), so a nullable rule returns `Some` with an empty span at any `pos`, matching Python; a literal §4.3 test against a nullable rule fails, or the implementer "fixes" the generator into Python divergence. Fixture grammar deliberately contains `?`/`*`, so the ambiguity was live.
Doc inspection: §3 bullet restated: "never panics, never indexes out of bounds ... a rule that cannot match empty returns `None`. A nullable rule ... returns `Some` with an empty span at *any* `pos`, including `-1` and `len+1` — identical to Python; not rejected. Covered by fixture tests calling `apply__parse_<rule>(-1)` and `(len+1)` on a non-nullable rule (asserting `None`) and on a nullable rule (asserting the empty match, pinning Python-equivalent behavior)." §4 item 3 test list updated to match ("non-nullable rule → `None`; nullable rule → empty match, per §3").
Assessment: contract restated per the reviewer's suggested fix, including the stronger option (additionally pinning the nullable-rule empty match); test scope split in both §3 and §4. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable; each fix verified in the design text against the reviewer's stated consequence.
