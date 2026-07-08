# Pre-pass dispositions — round 5, respond r1 a1

## slop-1
- Disposition: Fixed
- Action: `fltk/lsp/server.py:170` and `fltk/lsp/server.py:831` — replaced the "step3 same-file shape/behavior" phrasing with "same-file-only shape/behavior", describing the actual behavior without pointing at an ephemeral workflow milestone.
- Severity assessment: Low. The comment was accurate but leaked a development-process label ("step3") that has no meaning from the code alone; a future or out-of-tree reader has no "step3" to look up. Comment-hygiene standard applies — comments must stand alone.

## slop-2
- Disposition: Fixed
- Action: `fltk/lsp/test_gear_demo.py:74` — reworded "The requester's brief: ..." to state the invariant the test checks directly ("Comments/trivia, strings, numbers, ... must all be distinctly classifiable over the sample.").
- Severity assessment: Low. The comment referenced an external requester/task rather than the assertion's invariant; a note-to-self leaking from the authoring session. Rewritten to document the assertion on its own terms.
