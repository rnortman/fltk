# User directive — design re-pass

(Verbatim. Authoritative. Do not paraphrase or override.)

OK, I want to have a new designer take a pass over all of this with one thing in mind: Don't be stupid. FLTK is a framework for generating parsers that live *in a user application*, not in fltk. Users need control over the module name, the build process -- everything. Please review all these documents with that eye. I fear that these docs have been narrowly focused on making fltk dogfood its own grammar with Rust CST, but that is just a test case for the general capability.

## Directive 2 (verbatim, authoritative, supersedes any "static consumers unmodified" / TODO-deferral language)

Why do we think we're not allowed to modify fltk2gsm.py as part of this? Don't create a million TODOs to handle this later... just fucking do the work right now. Here is what I want out of this: At the end of this phase, when I use fltk to parse a grammar, *I CAN CHOOSE THE RUST CST BACKEND OR THE PYTHON CST BACKEND*. Of *course* that is going to include changes to the code taht imports the CST.

This is clearly yet another requirements change and design change and it's also exactly what I fucking said I wanted at the beginning of all of this and I'm getting sick of restating the basic fucking goal here.
