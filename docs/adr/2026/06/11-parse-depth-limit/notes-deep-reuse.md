reuse-1
File: crates/fltk-parser-core/tests/memo_toy.rs:461-462, 491-492, 514-515, 547-548
What's duplicated: T1, T2, T3, T4 construct token `Vec<String>` via
`vec!["(", …].into_iter().map(|s| s.to_owned()).collect()`.
Existing utility: `tokens(s: &str) -> Vec<String>` at memo_toy.rs:213, which maps
each char to a String — identical transformation for single-char-per-token inputs.
All four test inputs qualify: `(((1)))`, `(1)(1)`, `1+(((9)))` contain only
single-character tokens, so `tokens("(((1)))")`, `tokens("(1)(1)")`, etc. would
produce the exact same `Vec<String>`.
Consequence: the inline construction pattern evolves separately from `tokens()`; if
a future refactor changes how tokens are represented, the depth tests silently diverge
from the existing test infrastructure that uses `tokens()`.
