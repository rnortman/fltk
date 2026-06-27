# Error-handling review — final deep pass (full feature scope)

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2
Base: 6f975ebf3e4e102c256397337a5d11a21cc1ab7f

---

## errhandling-1

**File:line** `fltk/unparse/gsm2unparser_rs.py:586`

**Broken error path** In `_item_spacing_lines`, `spacing` and `ctor` are assigned only inside `if position == "before"` / `elif position == "after"` branches. The `if spacing is None` guard on line 586 and the `spec_expr` f-string on line 597 both reference those names unconditionally below the branches. If `position` takes any value other than the two expected strings at runtime, Python raises `UnboundLocalError: local variable 'spacing' referenced before assignment`.

**Why** The comment claims Pyright's `Literal["before", "after"]` annotation makes a runtime guard unnecessary. That is true at type-check time, but Python's `Literal` is erased at runtime; `_item_spacing_lines` is a private method and can be reached via subclassing or direct call without Pyright involvement. Every other unrecognized-branch site in this file (`_gen_rule_entry`, `_item_anchor_lines`, `_item_disposition_success_lines`, `_gen_term_body`) uses an explicit `raise RuntimeError/ValueError` with rule and item context. This site does not.

**Consequence** A wrong `position` value (a programming error in a future caller or subclass) surfaces as `UnboundLocalError` from line 586 with no mention of the rule name, item, or what value `position` carried. On-call cannot immediately identify the call site or config entry that triggered it, unlike every other generation-time error in this file which names the rule and item.

**What must change** Add `else: raise RuntimeError(f"Internal error: unexpected position {position!r} for rule {rule_name!r} item {item_id}")` after the `elif` block, where `item_id` mirrors the pattern used in `_item_disposition_success_lines`. This keeps the site consistent with the codebase's explicit-raise philosophy and makes the failure identifiable at the call site.

---

## errhandling-2

**File:line** `crates/fegen-rust/src/unparser.rs:59` (representative; identical pattern at ~17 trivia-handling sites: 59, 148, 183, 215, 251, 346, 433, 465, 537, 570, 603, 636, 818, 851, 1129, 1400, 1432); generator template at `fltk/unparse/gsm2unparser_rs.py:1351–1368`

**Broken error path** Every non-trivia rule's inter-item separator block has the shape:
```rust
if self._has_preservable_trivia(&trivia_node) {
    if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {
        acc = acc.add_trivia(...);
    }
    // no else arm
}
```
`_has_preservable_trivia` confirms a comment child variant is present. `unparse__trivia` then additionally checks child labels (`Some(TriviaLabel::LineComment)`, etc.) and calls `span.text()?` on each content span. A label mismatch or a sourceless content span causes `unparse__trivia` to return `None` after `_has_preservable_trivia` already returned `true`. The `None` is silently discarded, no separator spec is emitted, and the comment is dropped from the formatted output.

**Why** There is no `else` arm and no log call for the `None` path. The generator template (`gsm2unparser_rs.py:1351`) explicitly acknowledges this as `TODO(unparser-none-path-diagnostics)`, but this TODO is not in the user-accepted deferred set.

**Consequence** Comments present in the source are silently absent from formatted output. The formatter exits 0. Nothing appears on stderr. On-call cannot distinguish "formatter ran correctly" from "formatter ran and silently deleted comments." Since `_has_preservable_trivia` already confirmed a comment exists in the children array, reaching the `None` branch is an invariant violation, not a normal control-flow path; the code treats it as a no-op instead of reporting or halting.

**What must change** The generator (`gsm2unparser_rs.py`, method `_gen_non_trivia_rule_processing`) must emit an `else` clause inside the `_has_preservable_trivia` arm:
```rust
} else {
    // Invariant: _has_preservable_trivia confirmed a comment child but unparse__trivia
    // returned None (sourceless/mislabeled span). Log and continue rather than silently drop.
    eprintln!("fltkfmt internal: unparse__trivia returned None despite preservable trivia");
}
```
Or halt with `unreachable!()` / `debug_assert!(false, ...)` if the project philosophy for invariant violations is to crash. `unparser.rs` is generated ("do not edit"); the fix is in the generator only.

---

## errhandling-3

**File:line** `crates/fegen-rust/src/unparser.rs:1676` (`Identifier::Name`), `1707` (`RawString::Value`), `1738` (`Literal::Value`), `1941` (`LineComment::Content`), `1996` (`BlockComment::Content`), `2011` (`BlockComment::End`); generator template at `fltk/unparse/gsm2unparser_rs.py:1077–1084`

**Broken error path** Each labeled-Span item extracts text with `let text = span.text()?;`. When `span.text()` returns `None` (sourceless or sentinel span), `?` propagates `None` up through the call chain — `unparse__trivia` → callers — to the public `unparse_grammar` / `unparse_*` entry point, which returns `None`. In the fltkfmt CLI path, `run_inner` receives `Err("internal error: unparser returned None for a successfully parsed tree")` and emits `<filename>: internal error: unparser returned None for a successfully parsed tree` to stderr.

**Why** Every intermediate `?` discards context: which rule, which label, which span index caused the failure. By the time the caller observes `None`, all diagnostic information is gone. This is acknowledged as `TODO(unparser-none-path-diagnostics)` but not in the user-accepted deferred set.

**Consequence** On-call receives a message that names the input file but gives no information about which rule or which span triggered the failure. For token-content spans (lines 1676, 1707, 1738), `None` reaching the top is an invariant violation in the fltkfmt pipeline (the Rust parser always attaches source when called with `capture_trivia=true`). On-call cannot distinguish "span was legitimately empty" from "internal CST inconsistency" without re-running with a debugger attached to the generator's output.

**What must change** In the generator (`gsm2unparser_rs.py`, in `_gen_regex_term_body` and the span-text extraction paths), replace bare `span.text()?` with a logged-then-propagate pattern:
```rust
let Some(text) = span.text() else {
    eprintln!("fltkfmt internal: span for label {:?} has no source text", child_tuple.0);
    return None;
};
```
The generator has access to the label name at emission time and can embed it as a string literal, giving on-call the rule and label in the log line. The fix is in the generator only; `unparser.rs` is generated and must not be hand-edited.
