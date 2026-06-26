# Requirements (verbatim user spec)

I want a designer to design a fix: pure-Python parsers use Python span and Python CST. Rust parsers use Rust span and Rust CST. The user decides whether they want all-Python or all-Rust based on which parser they import. The span protocol and CST protocols allow a consumer to swap the parser while all of the CST-consuming code remains agnostic to which backend was used to produce the CST.

## Standing context from earlier in this session (verbatim user statements)

- "It is incorrect for the pure-Python parsers to use Rust-backed span."
- Original report: "If you run a generated python parser but don't have `fltk._native` available, we print a warning. This is noisy. There's nothing wrong with that module being missing from a *pure python* generated parser. Please locate and remove all such warnings."
