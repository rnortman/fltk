# User notes — requirements gate (verbatim chat directives)

1. It needs to be possible to write backend-agnostic type annotations, when writing code that lives above the level that decided which backend to use, so that backends are still swappable between Python and Rust.

2. If I understand the fltk-cst-regen-squeeze concern correctly, it is a non-concern: We run `make fix` after regen and that fixes the annotation formatting. We need to capture that somewhere so agents quit complaining about it: This is *normal* that we generate code that doesn't pass the formatter, and this is why `make fix` exists. Maybe we capture that in CLAUDE.md?
