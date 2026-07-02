# Deep quality review — protocol-module-truthiness-gate burndown

Reviewed: 5ce1fd8..cc1e869 (HEAD cc1e869c09866461a967f1b39e3e187c87400baf)

Scope of pass: read the full diff plus surrounding code in `gsm2tree_rs.py` (imports,
`__init__`, `generate_protocol` at HEAD), `gsm2tree.py` gate region, and both test files.
Verified: the workaround deletion leaves no dead imports (`CstGenerator`,
`create_default_context`, `pyreg` are all still used by `RustCstGenerator.__init__`);
no stray `TODO(protocol-module-truthiness-gate)` markers remain; the parameter is
threaded keyword-only with no default on the private helpers, matching the design; the
new tests pin the trap, the independence invariant, the opt-out, and same-instance
reuse. The core change is a genuine net improvement — sentinel deleted, throwaway
generator deleted, dead context allocation gone.

## quality-1 — leftover design-doc reference in the docstring this diff rewrote

- File: `fltk/fegen/gsm2tree_rs.py:478` (`generate_protocol` docstring, first paragraph)
- Issue: The diff rewrote the second paragraph of this docstring and the slop-respond
  round (commit cc1e869) explicitly hunted `(design §…)` refs — five were removed per
  `dispositions-prepass.md` — but the kept paragraph of the *same docstring* still ends
  with `(design §2.2)`. That points at `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/`
  workflow material, exactly the rot class the respond round was fixing.
- Consequence: The comment-hygiene rule was applied inconsistently within a single
  docstring; the surviving ref rots when the doc is archived/renumbered, and its
  presence next to freshly-scrubbed text teaches future editors that design refs are
  acceptable here.
- Fix: Drop `(design §2.2)` — the sentence stands on its own. While in there, tighten
  the new paragraph: "produces byte-identical bytes" is redundant ("byte-identical"
  appears three times in this docstring); "produces identical output with no side
  effects" suffices, letting the final sentence carry the byte-identity claim once.

## quality-2 — copy-pasted test builder helpers

- File: `fltk/fegen/test_cst_protocol.py:66-71` (`_build_builtins_cst_generator`)
- Issue: The new helper is `_build_cst_generator` (lines 59-64) copied verbatim except
  for the `py_module` argument — same grammar parse, same trivia-rule injection, same
  context construction.
- Consequence: Two helpers that must stay in lockstep. When grammar setup changes
  (e.g. a new preprocessing step or a different context), one copy gets updated and
  the other silently diverges — and because `test_protocol_text_independent_of_py_module`
  compares their outputs, divergence in setup would masquerade as (or mask) a
  py_module-dependence failure.
- Fix: Parameterize the existing helper —
  `def _build_cst_generator(py_module: pyreg.Module = pyreg.Module(["fltk", "fegen", "fltk_cst"])) -> ...`
  (or accept `py_module=pyreg.Builtins` at the two new call sites) and delete
  `_build_builtins_cst_generator`.

## quality-3 — section comment references the ephemeral burndown workflow

- File: `fltk/fegen/test_cst_protocol.py:75` — section header
  `# emit_kind_literal parameter (protocol-module-truthiness-gate burndown)`
- Issue: The parenthetical names a workflow event (the TODO burndown) and a slug that
  no longer exists anywhere — this diff deleted it from both `TODO.md` and the code.
  That is changelog/history commentary, the same class the respond round scrubbed from
  the docstrings in this very file.
- Consequence: Future readers grep for the slug and find nothing; the comment describes
  how the tests came to exist rather than what they cover, and rots into noise once the
  burndown context is forgotten.
- Fix: `# emit_kind_literal parameter` (the test docstrings already carry the rationale).

No other findings. Observability is not applicable here (pure codegen text emission,
no new error paths); the parameter addition is the anti-sprawl fix, not sprawl; the
kept `kind: object` arm is a deliberate, documented decision per the design.
