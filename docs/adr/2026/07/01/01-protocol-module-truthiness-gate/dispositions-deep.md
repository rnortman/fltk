# Deep review dispositions — protocol-module-truthiness-gate

Round 1. Base 5ce1fd8f936240169be9dafafa4bc63e46274a9d.

Reviewers with no findings: error-handling, correctness, security, test, reuse, efficiency.
Only quality-reviewer reported findings (quality-1..3), all confirmed against source.

## quality-1
- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:433` — dropped the stale `(design §2.2)` ref from
  `generate_protocol` docstring (the prior respond round scrubbed sibling refs in the same
  docstring; this one survived inconsistently). Also tightened the redundant "produces
  byte-identical bytes" to "produces identical output" (`gsm2tree_rs.py:439`), leaving the
  byte-identity claim carried once by the final sentence.
- Severity assessment: Doc-hygiene only; the surviving ref rots when the ADR dir is
  archived/renumbered and models design refs as acceptable in code. No behavior impact.

## quality-2
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:58` — deleted the near-verbatim
  `_build_builtins_cst_generator` helper and parameterized `_build_cst_generator` with an
  optional `py_module` (default None → real module path; pass `pyreg.Builtins` for the
  builtins-backed case). Updated the two call sites (tests at ~85 and ~94) to
  `_build_cst_generator(pyreg.Builtins)`. Used `None` default + in-body resolution to avoid
  ruff B008 (function call in argument default).
- Severity assessment: Duplication risk — the two helpers had to stay in lockstep, and the
  independence test compares their outputs, so setup drift could mask/masquerade as a real
  failure. Consolidation removes that latent hazard. No behavior change; 23 tests pass.

## quality-3
- Disposition: Fixed
- Action: `fltk/fegen/test_cst_protocol.py:73` — simplified the section header from
  `# emit_kind_literal parameter (protocol-module-truthiness-gate burndown)` to
  `# emit_kind_literal parameter`, dropping the ephemeral workflow/slug reference (the slug
  was deleted from TODO.md and code by this change).
- Severity assessment: Comment-hygiene only; the parenthetical named a now-nonexistent slug
  and described how the tests came to exist rather than what they cover. No behavior impact.
