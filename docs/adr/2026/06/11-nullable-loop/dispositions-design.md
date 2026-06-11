# Dispositions: nullable-loop design review, round 1

Concise. Precise. Complete. Unambiguous. No padding.

All three findings fact-checked against source at the working tree; all confirmed accurate; all fixed in `design.md`.

design-1:
- Disposition: Fixed
- Action: §2.3 quoted generated loop corrected from `while (one_result := <consume>) is not None:` to `while one_result := <consume>:`, with a citation of `compile_while` (`fltk/iir/py/compiler.py:277-282` — condition emitted as `({var} := {expr})`, bare truthiness) and committed `fltk/fegen/fltk_parser.py:134` (`while one_result := self.apply__parse_rule(pos=pos):`). Verified both sources directly; reviewer's claim is correct.
- Severity assessment: Moderate — the §5.4 `ast.unparse` source assertion written against the wrong quoted form (`is not None`) could never pass, burning a debugging cycle during the mandated failing-test-first phase. No design-structure impact.

design-2:
- Disposition: Fixed
- Action: §5.1 dep spec corrected to `fltk-cst-core = { path = ..., default-features = false }`, citing `crates/fltk-cst-core/Cargo.toml` (`default = ["python"]`) and the precedent in `crates/fltk-parser-core/Cargo.toml`; also notes `fltk-parser-core` has no `python` feature (manifest comment: "No `python` feature ... never links pyo3"). Verified both manifests directly; reviewer's claim is correct.
- Severity assessment: Moderate — the literal prior wording ("`python` feature off") would pull pyo3 into the standalone test binary, at minimum inflating the per-session build cost and at worst failing the link with a misleading error, blocking the mandatory pre-fix hang demonstration.

design-3:
- Disposition: Fixed
- Action: §2.5 rewritten to state the `make gencode` output set is authoritative (Makefile:148-180) and to enumerate the full regenerated-parser list, adding the previously omitted `bootstrap_parser.py`, `bootstrap_trivia_parser.py`, `toy_parser.py`, `toy_trivia_parser.py`, `unparsefmt_trivia_parser.py`. Verified the Makefile `gencode` target directly; reviewer's enumeration is correct.
- Severity assessment: Low-moderate — understated regen diff scope could trigger a false out-of-scope flag at scope review, or a partial regen leaving committed generated code stale and failing `make check`. No behavioral impact.
