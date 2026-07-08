# Pre-pass dispositions — round 5, respond r1 a2 (rework)

Judge returned REWORK on slop-1: the fix at `server.py:170`/`:831` was correct but the same
defect class ("step3" workflow labels in permanent comments) survived at two more locations in
this round's own added code. Only slop-1 was disputed; slop-2 stands as previously Fixed.

## slop-1 (rework)
- Disposition: Fixed
- Action: Swept the remaining "step3" workflow-milestone labels out of this round's diff.
  `fltk/lsp/test_server_crossfile.py:288` ("byte-identical to step3") → "stays same-file-only";
  `fltk/lsp/test_server_crossfile.py:302` ("the step3 behavior") → "the same-file-only behavior".
  Combined with the r1-a1 fixes at `fltk/lsp/server.py:170` and `:831`, a repo-wide grep for
  `step[0-9]` across `fltk/lsp/` and `examples/gear/` now returns no matches. `test_server_crossfile.py`
  full module passes (10 passed).
- Severity assessment: Low. Comments were accurate but leaked a development-process label ("step3")
  with no meaning from the code alone; a future or out-of-tree reader has no "step3" to look up.
  Comment-hygiene standard applies — comments must stand alone.

## slop-2
- Disposition: Fixed (unchanged from r1-a1)
- Action: `fltk/lsp/test_gear_demo.py:74` — reworded "The requester's brief: ..." to state the
  invariant the test checks directly. Not disputed by the judge.
- Severity assessment: Low. The comment referenced an external requester/task rather than the
  assertion's invariant; rewritten to document the assertion on its own terms.
