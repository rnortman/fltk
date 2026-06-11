# Judge verdict — design review

Concise. Precise. Complete. Unambiguous. No padding.

Phase: design. Doc: `docs/adr/2026/06/11-nullable-loop/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 3 findings.

## Findings walk

### design-1 — Fixed
Claim: §2.3 quoted the generated loop as `while (one_result := <consume>) is not None:`, but the compiler emits bare-truthiness walrus; consequence: §5.4 `ast.unparse` assertion written against the quoted form can never pass, burning a TDD debugging cycle.
Source check: `compile_while` (`fltk/iir/py/compiler.py:277-282`) emits `({var} := {expr})` with no `is not None`; committed `fltk/fegen/fltk_parser.py:134` reads `while one_result := self.apply__parse_rule(pos=pos):`. Finding accurate.
Design now: §2.3 quotes `while one_result := <consume>:` and cites both `compile_while` and the committed parser line inline.
Assessment: fix addresses the comment at the named section; severity should-fix. Accept.

### design-2 — Fixed
Claim: §5.1 said "`python` feature off" for the standalone Rust test crate, but `fltk-cst-core`'s `python` feature is default-on, so the dep must be declared `default-features = false`; consequence: pyo3 pulled into the standalone binary, inflating build cost or failing the link, blocking the mandatory pre-fix hang demonstration.
Source check: `crates/fltk-cst-core/Cargo.toml:18` — `default = ["python"]`; `crates/fltk-parser-core/Cargo.toml:10-15` — no `python` feature, and its own dep uses `fltk-cst-core = { path = "../fltk-cst-core", default-features = false }` (the cited precedent). Finding accurate.
Design now: §5.1 specifies `fltk-cst-core = { path = ..., default-features = false }`, cites the default-on feature and the precedent, and notes `fltk-parser-core` has no `python` feature.
Assessment: fix addresses the consequence exactly; severity should-fix. Accept.

### design-3 — Fixed
Claim: §2.5's regenerated-file enumeration omitted `bootstrap_parser.py`, `bootstrap_trivia_parser.py`, `toy_parser.py`, `toy_trivia_parser.py`, `unparsefmt_trivia_parser.py`; consequence: understated regen diff invites a false out-of-scope flag at scope review, or a partial regen fails `make check`.
Source check: Makefile `gencode` target generates fegen, bootstrap, toy, and unparsefmt Python parser pairs plus the fixture and fegen `parser.rs` — matches the reviewer's enumeration. Finding accurate.
Design now: §2.5 states the `make gencode` output set is authoritative (Makefile:148-180) and enumerates all ten regenerated parser artifacts, including the five previously omitted.
Assessment: fix adopts both halves of the reviewer's proposed remedy; severity nit-to-should-fix. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable; every fix verified against the revised design and source.
