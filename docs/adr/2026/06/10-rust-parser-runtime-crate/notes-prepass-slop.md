slop-1
File: crates/fltk-parser-core/src/errors.rs:263-268
Quote:
```rust
let name = if rule_names.get(rule_id as usize).is_some() {
    name.to_owned()
} else {
    format!("<unknown rule {rule_id}>")
};
```
What's wrong: `name` is already set by `.get().copied().unwrap_or("<unknown>")` two lines above. The second `if/else` repeats the same bounds check and overwrites `name` with a more-informative string, making the first `.unwrap_or` dead code. The intent is clear but the two-step resolution is redundant and confusing.
Consequence: Reads like an author who forgot the first fallback was there — a reviewer will stop and puzzle over what `name` contains going into the block, and may assume the first default `"<unknown>"` is reachable in production (it isn't).
Fix: Collapse into one expression:
```rust
let name = rule_names.get(rule_id as usize).copied()
    .map(|s| s.to_owned())
    .unwrap_or_else(|| format!("<unknown rule {rule_id}>"));
```

slop-2
File: crates/fltk-parser-core/src/memo.rs:861
Quote: `let _ = recursion; // consumed`
What's wrong: `recursion` is a local binding that goes out of scope at the end of the function anyway; this line does nothing except signal that the author was uncertain about ownership. The comment "consumed" is misleading because `recursion` is not `move`d into anything — it's just dropped.
Consequence: The comment actively misleads reviewers into thinking `recursion` was `move`d somewhere or that silencing a warning here is meaningful. Neither is true. Looks like an LLM left a bookmark.
Fix: Delete the line entirely.

slop-3
File: crates/fltk-parser-core/src/span.rs (SourceText::text docstring), lines 68-76
Quote:
```
/// Native-only accessor (not a ``#[pymethods]`` addition — the Python-visible
/// ``SourceText`` surface stays construction-only per ``terminalsrc.py``'s
/// portability contract). Used by ``fltk-parser-core``'s ``TerminalSource``
/// to read the text back without keeping a second copy.
```
What's wrong: The comment describes the *caller* (`fltk-parser-core`'s `TerminalSource`) and references an external Python file by name, turning a library docstring into a task-tracking note. "Used by X" is task-authoring context, not API documentation.
Consequence: The docstring tells future maintainers that only one specific caller may ever use this method, which is both incorrect and will become stale as the codebase grows. Reads as LLM narrating its own code-writing process.
Fix: Replace with intent + invariant: e.g. `/// Borrow the underlying source text. The returned reference is valid for the lifetime of this \`SourceText\`.`
