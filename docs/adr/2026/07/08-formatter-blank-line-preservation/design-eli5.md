# ELI5: Fixing blank-line preservation in the formatter

## What this is about

FLTK is a toolkit for building parsers and formatters. You write a grammar file that describes
a language, and FLTK generates a parser (which reads source code into a tree structure) and a
formatter (which takes that tree and prints it back as nicely-formatted text). Both the parser
and formatter are generated code -- you describe the language and formatting rules, and FLTK
produces programs that handle the actual work.

One of the things FLTK's formatter can do is preserve blank lines between top-level items. If
you write code where function definitions are separated by blank lines, you probably want those
blank lines to survive formatting. This is controlled by a configuration directive called
`preserve_blanks` that lives in a `.fltkfmt` file alongside your grammar. Setting
`preserve_blanks: 1` tells the formatter "keep up to one blank line between items when the
source has one."

The bug: a demo project called "gear" (an example language shipped with FLTK) has
`preserve_blanks: 1` in its formatter config, but formatting collapses all blank lines between
top-level items -- `use` statements, `shape` blocks, `const` declarations, and `fn` definitions
all get jammed together with no visual breathing room. The directive is present and should work,
but blank lines vanish anyway.

The investigation found that this is caused by two independent bugs that both need to be fixed.
Neither fix alone is sufficient.

## How the formatter pipeline works (just enough to follow the rest)

Three pieces matter:

1. **Formatter configuration.** A `.fltkfmt` file contains directives that control formatting
   behavior. FLTK parses this file into a `FormatterConfig` object in memory. One field on
   that object is `trivia_config`, which holds settings for how "trivia" is handled. (Trivia is
   a parser term for content that is syntactically insignificant -- whitespace and comments.
   It does not affect what the program means, but it does affect how the source looks.)

2. **Code generation.** FLTK does not interpret the grammar and config at format-time. Instead,
   it reads them once and generates a formatter program (in Python or Rust) that is specialized
   for that particular language. The generated formatter has the config baked in -- values like
   `preserve_blanks` become compile-time constants in the generated code. If
   `preserve_blanks` is 0 at generation time, the generated formatter simply does not contain
   any code path for preserving blank lines.

3. **Trivia in the syntax tree.** When the parser reads source code, whitespace between tokens
   gets captured in the tree as trivia nodes. The formatter later inspects these trivia nodes to
   decide whether the original source had blank lines. A blank line shows up as two or more
   consecutive newline characters (`\n\n`) inside the whitespace.

## Bug 1: Config directives clobbering each other

The `trivia_config` object has two independent settings: `preserve_blanks` (an integer --
how many blank lines to keep) and `preserve_node_names` (a set of names -- which trivia node
types to preserve verbatim, e.g. comments). These are set by two separate directives in the
`.fltkfmt` file:

- `preserve_blanks: 1;` sets the `preserve_blanks` field.
- `trivia_preserve: LineComment;` sets the `preserve_node_names` field.

The config parser processes directives in the order they appear in the file. The two handlers
for these directives treat the shared `trivia_config` object differently:

- The `preserve_blanks` handler **mutates** the existing `trivia_config` in place (creating a
  fresh default one first if none exists yet), then sets only the `preserve_blanks` field on it.
- The `trivia_preserve` handler **replaces** the entire `trivia_config` with a brand-new object,
  passing in only the node names. Everything else on the old object -- including
  `preserve_blanks` -- is discarded, because the new object gets the default value of 0.

If `trivia_preserve` comes after `preserve_blanks` in the file, the replacement wipes out the
`preserve_blanks` value that was just set. The gear config file lists them in exactly this
order (`preserve_blanks` first, `trivia_preserve` second), so the final config has
`preserve_blanks = 0` even though the file says `1`.

Every other `.fltkfmt` file in the repository happens to list them in the opposite order
(`trivia_preserve` first), where the mutate-in-place handler runs second and everything works.
Every existing test either uses that non-clobbering order or bypasses config parsing entirely by
constructing the config object directly in Python. That is why this bug was never caught before:
gear's config is the only one with the "wrong" order.

### The fix

Make the `trivia_preserve` handler work the same way as the `preserve_blanks` handler: mutate
the existing `trivia_config` in place instead of replacing it. If no `trivia_config` exists
yet, create a default one first, then set only the `preserve_node_names` field. This way each
directive owns its own field, and statement order between the two is irrelevant. If the same
directive appears more than once, last occurrence wins -- this was already the behavior and does
not change.

### Why not just reorder the gear config file

Reordering the directives in `gear.fltkfmt` would make gear work, but any out-of-tree user
whose `.fltkfmt` uses the same order would remain broken. The file keeps its current order
deliberately so it serves as a regression test that exercises the fixed code path.

## Bug 2: Newline counting blind to node-wrapped whitespace

Fixing bug 1 alone is not enough -- this was verified by running the fix in isolation. With
`preserve_blanks = 1` reaching the code generator, the generated formatter does contain the
blank-line-detection code path, but at runtime it still reports zero newlines in every trivia
gap, so blank lines still collapse.

Here is why. The generated formatter has a method called `_count_newlines_in_trivia` that looks
at the children of a trivia node and counts how many newlines are in the whitespace. But it
only counts newlines in children that are raw text spans -- direct, unstructured chunks of
source text. It skips children that are nodes (structured objects with their own type and
children).

This matters because of how gear's grammar defines its trivia rule. Most grammars (including
FLTK's own grammar for `.fltkg` files) use a default trivia rule where whitespace is captured
as a raw span. But gear defines a custom trivia rule:

```
_trivia := ( ws | line_comment )+ ;
ws := chars:/\s+/ ;
```

This means whitespace is captured as a `Ws` node (a named, typed object) rather than a raw
span. When the formatter encounters a blank line (`\n\n`) inside a `Ws` node, the newline
counter skips it because it is not a raw span -- it is a node. The counter returns 0, the
blank-line branch is never triggered, and the gap gets default spacing (a single newline).

### The fix

Extend the newline counter so it also checks node-typed children, not just raw spans. The rule:
if a trivia child is a node whose full source text is non-empty and consists entirely of
whitespace characters, count the newlines in it. Nodes that contain any non-whitespace (like
comments) contribute nothing -- this is important because a comment like `// hello\n` has a
newline as its terminator, and that newline should not be miscounted as evidence of a blank
line.

The whitespace-only test is done at runtime by inspecting the actual source text of the node,
not at code-generation time by analyzing the grammar's regex patterns. This is a deliberate
choice: determining from a regex whether it can only match whitespace would require regex
analysis and could misclassify edge cases. The runtime check is exact, cheap (a single pass
over a short string), and works identically in both the Python and Rust backends.

The implementation differs slightly between backends because the generated formatters are
structurally different:

- **Python backend:** A new runtime helper function is added (following the existing pattern of
  small helper functions in the runtime support module). The generated loop body simplifies to a
  single call to this helper instead of a conditional.
- **Rust backend:** The generator already knows the concrete types of trivia children at
  generation time (they are variants of an enum), so it emits a match arm for each node-typed
  variant that performs the whitespace-only check on the node's span text.

Both backends produce the same behavior: whitespace-only nodes contribute their newline counts,
everything else contributes zero.

## Why both fixes are needed together

Bug 1 prevents `preserve_blanks` from reaching the code generator at all -- the value is
silently set to 0, so the generated formatter has no blank-line-preservation logic. Bug 2
prevents the blank-line-preservation logic from working even when it is present, because the
newline counter cannot see newlines inside node-wrapped whitespace.

For gear specifically, fixing only bug 1 means the blank-line branch gets generated but never
fires (counter returns 0). Fixing only bug 2 is meaningless because the branch is never
generated (preserve_blanks is 0). Both fixes are required.

## What is not changed

- **The gear config file stays as-is.** Its directive order is the regression artifact that
  tests the fix.
- **The code that decides whether to emit blank-line branches in the generator** is untouched.
  Only the newline-counting method and the config parser change.
- **The spacing-resolution logic** (which decides what happens when multiple spacing directives
  apply to the same gap) is untouched. It already handles blank-line spacing correctly; it was
  just never receiving blank-line input from the trivia counter.
- **The LSP server** is untouched. It builds its formatter pipeline from the same config and
  generator functions, so it inherits both fixes automatically.

## Impact on users outside this repository

FLTK generates code that external projects use. The changes here touch only a private helper
method inside the generated formatter (the newline counter) and the config parser. No generated
public symbols, type signatures, or class names change.

Two classes of existing users benefit:

- Anyone whose `.fltkfmt` lists `preserve_blanks` before `trivia_preserve` currently has
  blank-line preservation silently ignored. After regenerating their formatter, it works.
- Anyone whose grammar wraps whitespace in named trivia rules (like gear does) and sets
  `preserve_blanks > 0` currently has blank lines collapse regardless of directive order. After
  regenerating, they are preserved.

Both are cases where the documented behavior of the directive was not being delivered. A user
could only be "relying" on the old behavior if they wrote a directive asking the formatter to
do something and simultaneously depended on it not doing it. No migration is needed beyond the
normal regenerate-and-reformat workflow.

## Cross-backend equivalence

FLTK has two code-generation backends: Python and Rust. The config parser (bug 1's fix) is
shared code -- there is only one config parser, used by both backends, so the fix applies to
both identically.

The newline counter (bug 2's fix) is not shared -- each backend has its own generator that
emits the counter. Equivalence is maintained the same way the rest of the mirrored code
maintains it: line-cited parity comments in the Rust generator that reference the corresponding
Python generator lines, plus mirrored tests that verify both sides.

## Test plan

Tests are written first (TDD) and must fail before the fix is applied, except where noted.

**Config parsing tests** pin bug 1. They parse `.fltkfmt` text with `preserve_blanks` before
`trivia_preserve` and verify that both settings survive in the resulting config. A reverse-order
test and a repeated-directive test pin the "fields are independent, last-per-field wins"
semantics.

**End-to-end rendering tests** through the parsed-config path close the gap left by existing
tests (which bypass config parsing). One test uses the clobbering directive order on a
standard grammar and verifies blank lines survive -- this pins bug 1 through the full pipeline.
Another set uses a custom-trivia grammar (like gear's, with node-wrapped whitespace) and verifies
both that blank lines survive and that comment-terminator newlines are not miscounted as blank
lines -- this pins bug 2.

**Unit tests** for the new Python runtime helper verify the four cases: raw span, whitespace-only
node, comment node, and empty-span node.

**Rust backend tests** mirror the config-path test (verifying bug 1 reaches the Rust generator)
and add generated-source-level checks for the new whitespace-only counting arm.

**Integration tests** at the gear-demo level: the already-committed failing test
(`test_formatting_preserves_blank_lines_between_items`) becomes the passing regression test.
Existing tests for idempotency and comment preservation must continue to pass.

**Full-suite regression**: all existing tests must remain green, including the Python-vs-Rust
byte-parity tests and the existing `preserve_blanks` tests that use direct-span trivia.

## Known adjacent gaps, deferred

**Rule-level preserve_blanks is parsed but never consumed.** The config system supports setting
`preserve_blanks` per grammar rule (not just globally), and there is code to parse and store it,
but neither code generator actually reads the per-rule value -- both read only the global
setting. This is a pre-existing feature gap, not caused by this bug, and gear's config does not
use it. It is deferred with a TODO marker.

## Open questions

None. The design resolves both judgment calls in its body: the unconsumed rule-level
`preserve_blanks` is deferred as a TODO (pre-existing gap, orthogonal to this bug), and the
whitespace-only check runs at runtime rather than via generation-time regex classification
(exactness, cheapness, and backend symmetry are the reasons).
