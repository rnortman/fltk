# Request

> This document substitutes for requirements. It is the user's request captured
> verbatim. Designer and reviewers must treat it as the authoritative spec.

## User request (verbatim)

`fltk._native` contains the *runtime for all fltk-generated parsers*. It contains
*nothing* specific to any specific grammar. No parsers. No cst. The fegen.fltkg
parser and cst go into their own module somewhere. This is exactly how the python
code is structured -- we 100% codegen the python fegen parser and cst, and the
runtime stuff is all in completely separate modules that are not codegen. The rust
side needs to be refactored to match. We need one more quick exploration which is
"this is how the python backend does it". Then those two explorations feed into a
designer. The designer is specifically supposed to *refactor as heavily as needed*
to clean this mess up; this is not the time to be lazy and worry about breaking
external consumers because there are no external consumers of the rust backend yet
-- the only out of tree consumer is the spike that we did locally in ~/tps/clockwork
and we haven't even pushed that anywhere yet, it's still just a research test.
