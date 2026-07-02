# Quality review notes — unparser-source-helper

Reviewed: f07852a5ebb26c6c3534be0457f07ac5f13b4041 (base 007401edf41e4950929b01966d276450b1aead9b)

## quality-1

**Where:** `fltk/test_plumbing.py:258-269` (`TestUnparserSource.test_generate_unparser_execs_its_output`)

**Issue:** Near-verbatim copy of the existing `TestUnparsing.test_unparse_simple_expression`
(`fltk/test_plumbing.py:275-294`): same grammar (`expr := hello:"hello" , world:"world";`), same
input (`"helloworld"`), same parse → `generate_unparser` → `unparse_cst` → `render_doc` sequence —
just with a weaker assertion (rendered string equality instead of the structural doc check). More
importantly, the test never calls `generate_unparser_source`, so its docstring's claim — "pins the
exec contract" (i.e. that `generate_unparser` execs exactly the source `generate_unparser_source`
returns) — is not what it tests. Nothing in the suite actually ties the two public entry points
together; the design's stated test intent ("pinning the 'generate_unparser execs its output'
contract", design.md test plan) is unmet by this test.

**Consequence:** A duplicate test adds maintenance weight with zero marginal coverage, and its
misleading docstring makes future maintainers believe the source/exec single-sourcing contract is
guarded when it isn't. If someone later reintroduces a separate pipeline inside
`generate_unparser` (the exact drift this whole change exists to prevent), every test still
passes — the regression the TODO was about would land silently.

**Fix:** Make the test earn its name: on the same `(grammar, cst_module_name)` inputs, exec the
string returned by `generate_unparser_source` and assert the exec'd `Unparser` class behaves
identically to `generate_unparser(...).unparser_class` (e.g. unparse the same CST through both and
compare `render_doc` output, or at minimum assert both classes expose the same `unparse_*`
surface). Alternatively, if the contract is deemed untestable-cheaply, delete the test and the
docstring claim rather than keep a duplicate of `test_unparse_simple_expression`.

---

No other findings. The refactor itself is clean: the split into `_assemble_unparser_module` +
two thin public/exec wrappers is the right shape, the 3-tuple return avoids recomputing the
trivia grammar, no comment-hygiene violations were introduced in the diff, and the
`test_is_span_guard.py` helper reduction removes the duplicated pipeline as intended.
