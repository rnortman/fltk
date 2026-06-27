## errhandling-1

**File:line** `crates/fegen-rust/src/unparser.rs:60` (representative; identical pattern at ~17 trivia-handling sites: 60, 148, 183, 215, 251, 346, 433, 465, 537, 570, 603, 636, 818, 851, 1129, 1400, 1432)

**Broken path** Every rule-level trivia-handling block has the shape:
```rust
if self._has_preservable_trivia(&trivia_node) {
    if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {
        acc = acc.add_trivia(...);
    }
    // no else — None silently discarded
}
```
`_has_preservable_trivia` checks child *variants* (type); `unparse__trivia` additionally gates on child *labels* (`Some(TriviaLabel::LineComment)` / `Some(TriviaLabel::BlockComment)`) and also uses `span.text()?` for each comment's content span (lines 1941, 1996, 2011 — see errhandling-2 below). Either a label mismatch or a sourceless/sentinel content span causes `unparse__trivia` to return `None` after `_has_preservable_trivia` returned `true`. The `None` is silently discarded.

**Consequence** Comments present in the source are silently dropped from formatted output. No log message, no panic, no counter, no error return. On-call observing a formatted file with missing comments has zero diagnostic signal — nothing in stderr, nothing in any log — to distinguish "formatter ran correctly and produced correct output" from "formatter ran and silently deleted comments." Because `_has_preservable_trivia` is only called when the comment types are already confirmed in the children array, reaching the `None` branch is an invariant violation; the code treats it as a no-op.

**What must change** The generator (`fltk/unparse/gsm2unparser_rs.py`, in the method that emits the `_has_preservable_trivia`/`unparse__trivia` block for each separator site) must emit an `else` clause:
```rust
} else {
    // Invariant violated: _has_preservable_trivia confirmed comments exist
    // but unparse__trivia failed to match them.
    eprintln!("fltkfmt internal error: unparse__trivia returned None \
               despite _has_preservable_trivia == true (sourceless/mislabeled span?)");
}
```
Or, if the project philosophy for an invariant violation is to halt, `unreachable!()` / `debug_assert!(false, ...)`. `unparser.rs` is generated ("do not edit"); the fix is in the generator only.

---

## errhandling-2

**File:line** `crates/fegen-rust/src/unparser.rs:1676` (`Identifier::Name`), `1707` (`RawString::Value`), `1738` (`Literal::Value`), `1941` (`LineComment::Content`), `1996` (`BlockComment::Content`), `2011` (`BlockComment::End`)

**Broken path** Each labeled-Span item in the generated unparser extracts span text with `let text = span.text()?;`. When `span.text()` returns `None` (no source attached, or negative / sentinel start/end), `?` propagates `None` up through the enclosing `unparse_<rule>` call chain to the nearest public entry point:

- For token-content spans (lines 1676, 1707, 1738): `None` chains all the way to `unparse_grammar → None`. In the Python binding (`crates/fegen-rust/src/unparser.rs:2068-2069`) this becomes `Ok(None)` — Python receives `None` with no exception, no error string, and no indication of which node or which span failed.
- For comment-content spans (lines 1941, 1996, 2011): `None` chains to `unparse__trivia → None`, which is then silently swallowed by the pattern described in errhandling-1.

In both cases every intermediate `?` discards context: by the time the caller observes `None`, the information about *which span* lacked source and *why* is gone.

**Consequence** A Python caller receiving `None` from `unparse_grammar` (or any public `unparse_*` method) cannot distinguish "grammar is structurally unparseable by this unparser" from "an identifier/literal/comment span in an otherwise-valid CST was missing its source reference." The latter is an invariant violation (the Rust parser attaches source to all spans when called as `Parser::new(src, filename, true)`); the former is a legitimate "parse succeeded but unparse failed" signal the API is designed to return. On-call has no log entry to start the diagnosis from.

**What must change** In the generator, for labeled Span items that extract text, replace bare `span.text()?` with a logged-then-propagate pattern, e.g.:
```rust
let Some(text) = span.text() else {
    eprintln!("fltkfmt internal error: span for {} has no source text", stringify!($label));
    return None;
};
```
The fix must be in the generator (`fltk/unparse/gsm2unparser_rs.py`, in the per-label Span item handler); `unparser.rs` is generated and cannot be hand-edited.
