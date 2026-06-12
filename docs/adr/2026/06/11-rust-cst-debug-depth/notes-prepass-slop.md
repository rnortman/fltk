slop-1
File: fltk/fegen/gsm2tree_rs.py (docstring on `_child_enum_block`, ~line 418)
Quote: "child_union: the sorted list of all node-typed child class names across all rules.\ninto_drop_item is emitted when this class appears in child_union..."
What's wrong: Docstring paragraphs added for `child_union` and `into_drop_item` describe implementation mechanics rather than contract or invariants. They restate what the code visibly does one line below, in a style that reads as an LLM narrating its own additions.
Consequence: Docstring inflation is a tell that the diff was not author-reviewed before submission. A reviewer reading the method signature already knows `child_union` is a list of child class names; the comment adds nothing a reader could not derive in two seconds.
Suggested fix: Drop the two added sentences; the existing docstring (Node-typed variants use Shared<T>...) plus the parameter name is sufficient. If the `needs_drop_item` condition logic is genuinely non-obvious, a single inline comment at the condition itself is better than polluting the docstring.

slop-2
File: fltk/fegen/gsm2tree_rs.py (generate(), ~line 382)
Quote: "# Pre-compute the child-class union once for _drop_block."
What's wrong: Comment states the obvious — that a variable computed before a loop is pre-computed. "once for _drop_block" is slightly more useful but is self-evident from the single call site.
Consequence: Noise comment; minor but contributes to the diff reading like narration.
Suggested fix: Remove the comment entirely, or if the motivation for pre-computing (avoiding O(N²) recomputation) is considered worth preserving, say that instead.

slop-3
File: fltk/fegen/gsm2tree_rs.py (_node_block docstring, ~line 460)
Quote: "impl Drop is emitted when the rule has node-typed children (child_classes non-empty)."
What's wrong: Docstring addition restates the `if child_classes:` guard two lines below verbatim in English. Docstring for a code-gen method should state intent/invariants, not mirror the conditional.
Consequence: Same tell as slop-1. Reads as narrated diff, not documentation.
Suggested fix: Remove or replace with the invariant that matters: why span-only nodes are safe to skip (no Shared<T> fields → drop glue is trivially non-recursive, and avoiding Drop sidesteps E0509).

slop-4
File: Multiple generated .rs files (e.g. crates/fltk-cst-spike/src/cst.rs:87, src/cst_fegen.rs:626, and every other node struct)
Quote: "/// Teardown is iterative: bounded stack at any depth."
What's wrong: This docstring line is emitted on every node struct including span-only nodes (Identifier, Trivia, Disposition, Quantifier, RawString) that have NO Drop impl. For those structs the statement is false — teardown is not iterative, it is the compiler's default drop glue, which happens to be trivially non-recursive only because there are no Shared children. Claiming "iterative" on a struct with no Drop impl is inaccurate.
Consequence: False documentation ships as public API docstrings on generated types consumed by downstream users. A downstream author reading `Identifier`'s rustdoc would be misled about its Drop behavior.
Suggested fix: Emit "Teardown is iterative: bounded stack at any depth." only when `child_classes` is non-empty (i.e., only when an impl Drop is actually emitted). For span-only nodes emit nothing, or emit "Teardown: no node-typed children; drop is trivially bounded."

slop-5
File: fltk/fegen/gsm2tree_rs.py (_drop_block, ~line 542-587) and all generated .rs files
Quote: (repeated per cls in child_union)
  "                // `shared` drops here: count==1 → childless node, trivial drop;"
  "                // count>1 → refcount decrement only. Either way, no recursion."
What's wrong: Identical two-line comment block is emitted once per variant arm in the match. With many node types the comment appears a dozen or more times in each generated file, verbatim. Comments that explain a pattern belong once, before the match or in a block comment, not copy-pasted into every arm.
Consequence: Generated files become noisy; the repetition itself is a tell that the comment placement was mechanical rather than deliberate. Does not affect correctness but is visible to anyone reading the generated code.
Suggested fix: Hoist the explanation to a single comment before the `match self {` block and remove it from each arm.
