## slop-1

**File**: `crates/fltk-unparser-core/src/accumulator.rs:~69`

**Quote**: `/// The generated unparser's non-trivia-rule separator processing reads this to skip / emitting a fresh separator spec right after a trivia child was already consumed / (port of the \`accumulator.last_was_trivia\` attribute read at \`gsm2unparser.py:1266\`).`

**What's wrong**: This is a public method docstring that names its callers ("The generated unparser's non-trivia-rule separator processing reads this") and narrates the implementation context ("port of the `accumulator.last_was_trivia` attribute read at…"). Neither belongs in a public API doc: callers belong in PR description, port-tracing belongs in commit history or an internal comment at most.

**Consequence**: A downstream consumer reading the `last_was_trivia()` API docs sees a description of someone else's caller, not the invariant the accessor exposes. Reads as LLM narrating its own work context to itself.

**Suggested fix**: `/// Returns \`true\` when the most recently added content was trivia.`

---

## slop-2

**File**: `crates/fltk-unparser-core/src/accumulator.rs:~291`

**Quote**: `// The public accessor mirrors the private flag the mutators set.`

**What's wrong**: Self-explanatory comment restating what the test body and test name already show. The test is named `last_was_trivia_accessor_reflects_state`; the comment adds nothing beyond that.

**Consequence**: Noise in a test module; the hallmark pattern of LLM commenting to narrate rather than illuminate.

**Suggested fix**: Remove the comment entirely.

---

## slop-3

**File**: `crates/fltk-unparser-core/src/doc.rs:~242`

**Quote**: `/// Port of the Python unparser's \`_create_separator_spec\` / (\`fltk/unparse/gsm2unparser.py:446\`): either \`spacing\` or \`preserved_trivia\` may`

**What's wrong**: Public `pub fn separator_spec` in the core crate opens its docstring with "Port of…", which is process/origin language describing where the function came from, not what it does. The rest of the docstring is informative, but the opening sentence frames this as a historical artifact of a porting process rather than a first-class API.

**Consequence**: External consumers of `fltk-unparser-core` (this is a library crate) see a docstring that reads as LLM narrating its own implementation step. The "Port of" sentence provides no information about when or why to call `separator_spec`.

**Suggested fix**: Drop the "Port of…" opening sentence; the behavioral description that follows ("either `spacing` or `preserved_trivia` may be absent…") is the actual documentation.

---

## slop-4

**File**: `tests/test_rust_unparser_generator.py:~941`

**Quote**: `"""A WS_REQUIRED gap in a trivia rule consumes the unlabeled whitespace Span and emits spacing. / The trivia-rule branch (\`\`gsm2unparser.py:1103\`\`) bounds-checks, matches the unlabeled / \`\`Span\`\` child, advances \`\`pos\`\`, counts newlines, and (preserve_blanks=0) emits a plain / \`\`HardLine\`\` for a newline or the default separator spacing otherwise.`

**What's wrong**: The docstring narrates the internal steps of the system under test ("bounds-checks, matches the unlabeled Span child, advances pos, counts newlines") instead of stating what the test proves. This pattern repeats across most of the new test functions: each docstring reads as LLM explaining to itself what the implementation does, step by step.

**Consequence**: The docstring duplicates the test body assertions and calls out implementation details that will become stale if the implementation evolves (e.g., a refactor that uses a different child-advance strategy). Reads as the test author narrating rather than testing.

**Suggested fix**: State the observable scenario and the expected outcome — one or two sentences. Example: `"""WS_REQUIRED in a trivia rule fails the alternative when no unlabeled whitespace Span is present at \`pos\`; when one is present it counts its newlines and emits the appropriate SeparatorSpec."""`

---

## slop-5

**File**: `fltk/unparse/gsm2unparser_rs.py:~1240`

**Quote** (generated code shape, from `_gen_non_trivia_rule_processing`):
```
if self._has_preservable_trivia(&trivia_node) {
    if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {
        acc = acc.add_trivia(separator_spec(None, Some(…), required));
    }
    // <- no else
} else {
    // newline-driven / default spacing
}
```

**What's wrong**: When `_has_preservable_trivia` returns `true` but `unparse__trivia` returns `None` (the trivia node failed to unparse), no separator spec is emitted — neither the preserved-trivia spec nor the newline/default fallback. The generated code silently produces no spacing at all for this case. There is no comment on the `if let Some(...)` block explaining that omitting the separator on unparse failure is intentional.

**Consequence**: A formatting regression where trivia that was supposed to be preserved but happened to fail unparsing causes the inter-token separator to vanish entirely, rather than falling back to default spacing. The silence makes it invisible in code review.

**Suggested fix**: Either add an `else` arm to the `if let Some(trivia_result)` that emits the newline-driven / default spacing (matching the `_has_preservable_trivia == false` path), or add a comment asserting the fall-through-with-no-output is the documented correct behavior for a failed trivia unparse.
