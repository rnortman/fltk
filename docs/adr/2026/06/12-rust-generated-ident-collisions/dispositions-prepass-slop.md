slop-1:
- Disposition: Fixed
- Action: Replaced four inline `gsm.Rule` copies in `test_multiple_collisions_reported_at_once` with two `_make_two_rule_grammar` calls merged via `gsm.Grammar(rules=g1.rules + g2.rules, identifiers={**g1.identifiers, **g2.identifiers})`. tests/test_gsm2tree_rs.py:1762-1776.
- Severity assessment: Readability / maintainability issue; no correctness risk. Four identical 12-line blobs where a two-liner sufficed.

slop-2:
- Disposition: Fixed
- Action: Replaced the prose INVARIANT comment with a module-level `assert` that checks no `_RESERVED_CLASS_NAMES` key starts with "Py" or ends with "Child"/"Label". fltk/fegen/gsm2tree_rs.py:46-52. The accompanying comment still documents why the invariant matters for future maintainers.
- Severity assessment: The prose comment was unenforceable; a future `_RESERVED_CLASS_NAMES` entry like "PyNode" would silently break collision coverage. The assertion turns a latent gap into an immediate startup failure.

slop-3:
- Disposition: Fixed
- Action: Removed the redundant `from fltk.fegen.gsm2tree_rs import RustCstGenerator as _Gen` local import from `test_prediction_vs_output_consistency`; replaced `_Gen` references with the module-level `RustCstGenerator`. tests/test_gsm2tree_rs.py:1851-1879.
- Severity assessment: Cosmetic only; no correctness or coverage impact. The `# noqa: PLC0415` suppression was masking a problem that did not exist.
