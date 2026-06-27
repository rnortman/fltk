## errhandling-1

**File:** `fltk/unparse/gsm2unparser_rs.py`, `_gen_non_trivia_rule_processing`, around the `if let Some(trivia_result)` block (diff lines +369–380 in the original diff output, full-file lines ~1248–1259).

**The broken error path:** When `_has_preservable_trivia` returns `true` but `unparse__trivia` returns `None`, the generated Rust code silently:
1. Advances `pos` past the Trivia child (consuming it).
2. Emits no separator spec (`acc` is not updated).
3. Emits no log, eprintln, or any other diagnostic.

The generated block is:

```rust
if self._has_preservable_trivia(&trivia_node) {
    if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {
        acc = acc.add_trivia(separator_spec(None, Some(trivia_result.accumulator.doc()), ...));
    }
    // No else: failure is silently swallowed.
} else {
    // newline-driven fallback
}
pos += 1;  // Trivia consumed regardless.
```

**Why:** The generator's docstring explicitly calls this out as "a faithful port of Python's `if_trivia_success` having no `orelse`" (`gsm2unparser.py:1321`). The Python backend is equally silent. Parity was the goal; observability was not.

**Consequence:** When `unparse__trivia` returns `None` for a Trivia child that `_has_preservable_trivia` classified as having preservable content, the Trivia node is consumed but its inter-item gap emits no separator doc at all. The caller's formatted output is silently wrong — items that should have a separator between them are rendered adjacently or with whatever the renderer defaults to on an absent SeparatorSpec. There is no runtime signal (not even `eprintln!` in the generated Rust, which has no logging infrastructure wired). An on-call engineer investigating "formatter dropped spacing between items" has nothing to diagnose the root cause: neither the CST node, the rule, nor the failure reason are recorded anywhere.

A trivia node that the parser accepted but the unparser cannot reproduce is either a grammar inconsistency or a generator bug; both are worth surfacing. The fix is for the generator to emit an `else` arm (after the `if let Some(trivia_result)`) that falls back to newline-driven / default spacing (the same path taken when `_has_preservable_trivia` returns `false`) rather than emitting nothing.

---

Commit reviewed: `1fcae0bbe0063b83b1883eb439ababc9da6916d4`
