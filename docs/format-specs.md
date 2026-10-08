# Format Specification Files (.fltkfmt)

Format specification files control how the FLTK unparser formats output. They use a simple DSL to specify spacing, grouping, and other formatting behaviors.

## Overview

A format spec file contains a series of statements that configure:

- **Default spacing** between grammar items
- **Trivia preservation** (comments and whitespace)
- **Blank line handling**
- **Per-rule formatting** overrides
- **Positional spacing** (before/after specific items)
- **Grouping and nesting** for line breaking

## Spacing Types

Spacing values control how whitespace appears between items:

| Spacing | Description |
|---------|-------------|
| `nil` | No space |
| `nbsp` | Non-breaking space (always renders as a space) |
| `bsp` | Breaking space (space if fits on line, newline if not) |
| `soft` | Soft break (nothing if fits on line, newline if not) |
| `hard` | Hard break (always newline) |
| `blank` | Hard break plus one blank line |
| `blank(N)` | Hard break plus N blank lines |

## Global Statements

### Default Spacing

Set default spacing for separator types in the grammar:

```
ws_allowed: nil;      // Default for "," separators
ws_required: bsp;     // Default for ":" separators
```

- `ws_allowed` - Spacing when whitespace is allowed (`,` separator in grammar)
- `ws_required` - Spacing when whitespace is required (`:` separator in grammar)

### Trivia Preservation

Specify which trivia node types to preserve from the source:

```
trivia_preserve: LineComment, BlockComment;
```

This preserves line comments and block comments in the formatted output. Without this, all trivia is discarded.

Preserved trivia binds to the gap it was written in, including around suppressed literals. A grammar whose statement rule ends `, %";" ,` has an empty gap between the value and the terminator and a real one after it, so a blank line or a comment written after the `;` renders after the `;`, and one written before it stays before it. The unparser decides this from source positions, not from child order: the parser contributes a child only where whitespace or a comment actually matched, and a suppressed literal contributes none at all, so the two sequences do not line up.

The binding falls back to child order wherever the tree's positions stop being positions in one source — a child or rule node whose span is sourceless or carries a different source, which is what hand-built and mutated CSTs produce, or anything past an optional suppressed non-literal (`%rule?`, `%/re/?`), which the unparser cannot reconstruct. In that fallback the unparser also does not refuse a trivia child no gap claimed, because ownership was never decided; elsewhere an unclaimed comment-bearing trivia child is an error rather than silently dropped output. The binding resumes at the next rule or terminal child carrying the rule node's own source.

One shape is neither owned nor an empty gap: a trivia child that starts *behind* the position the walk has reached, in the walk's own source. A parsed tree never produces one, so it means the walk passed the gap the trivia was written in, and every ownership answer after it would be a guess. The unparser halts there, naming the rule, the child position, both offsets and a line/col. A mutated CST can reach this by moving a trivia child's span backwards specifically; moving any other child's span out of order puts the cursor in the fallback above instead.

### Blank Line Preservation

Control whether blank lines from the source are preserved:

```
preserve_blanks: 1;   // Keep at most 1 blank line
preserve_blanks: 0;   // Collapse all blank lines (default)
preserve_blanks: 2;   // Keep at most 2 blank lines
```

`preserve_blanks: N` **caps**: a gap holding `B` blank lines in the source renders `min(B, N)` blank lines. Blank lines are never invented — a gap with no blank line in the source gets none — and never exceed `N`. With the default `preserve_blanks: 0` every blank line collapses, which is the canonical form the formatter otherwise enforces everywhere.

Blank preservation is the one deliberate exception to that canonical form, and it exists so source can carry logical grouping: groups of rules in a `.fltkg` file, groups of struct fields, runs of related functions — with or without a group-header comment above each group.

Blank lines are counted around preserved comments, not just around code. A blank line separated from the code by a preserved comment is still a blank line: in

```
a;

// group 2
b;
```

the blank before `// group 2` survives, and so does a blank placed *after* the comment or between two consecutive comments. A line comment's terminating newline is accounted for, so two adjacent comment lines with no blank between them do not gain one. This applies only to comments that `trivia_preserve` actually keeps; in a gap whose comments are dropped, the dropped comments' line terminators do not manufacture blank lines.

#### Scope of a rule-level override

A `preserve_blanks` inside a `rule` block governs the gaps in that rule's own layout — which is how you say "no blank lines inside an `expr`" while still allowing them between top-level items:

```
preserve_blanks: 1;

rule expr {
    preserve_blanks: 0;
}
```

The inverse works too: a global `preserve_blanks: 0` with a rule-level `preserve_blanks: N` opts a single rule in. The interior of a run of preserved comments follows the **global** setting, since the trivia is formatted by one shared routine with no enclosing-rule identity.

A `preserve_blanks` inside an `after` or `before` anchor block is an **error**. The grammar admits it, but there is no per-anchor blank policy, so the directive is rejected rather than silently ignored. Use a global or rule-level directive instead.

## Positional Spacing

### After

Specify spacing after a specific item:

```
after ";" { hard; }           // Newline after semicolons
after name { nbsp; }          // Space after the "name" label
after ":=" { bsp; }           // Breaking space after :=
```

### Before

Specify spacing before a specific item:

```
before ";" { nbsp; }          // Space before semicolons
before "|" { bsp; }           // Breaking space before |
before ")" { bsp; }           // Breaking space before )
```

Items can be referenced by:
- **Literal value**: `";"`, `"|"`, `"("`
- **Label name**: `name`, `value`, `item`

A `before X` on an included optional item (`X?`, `X*`) applies only when `X` is emitted: an
absent `?` item or a zero-occurrence `*` item contributes no spacing, and a non-empty `*` run
gets one spacing ahead of the run. Spacing anchored to a suppressed item (`%X?`, or an unlabelled
literal) fires whether or not the source carried the token, because formatted output may not
depend on a token the formatter does not print.

## Rule-Specific Configuration

Override formatting for specific grammar rules:

```
rule alternatives
{
    group;                    // Wrap entire rule in a group
    before "|" { bsp; }       // Breaking space before |
    after "|" { nbsp; }       // Space after |
}

rule item
{
    ws_allowed: nil;          // Override default ws_allowed
    after ":" { nil; }        // No space after : in labels
}
```

### Available in Rule Blocks

- `ws_allowed: <spacing>;` - Override default ws_allowed spacing
- `ws_required: <spacing>;` - Override default ws_required spacing
- `preserve_blanks: N;` - Override blank line preservation for gaps in this rule's own layout
- `group` / `nest` / `join` - Grouping directives
- `before` / `after` - Positional spacing
- `omit` / `render` - Item disposition

## Grouping and Line Breaking

Grouping controls how the formatter decides where to break lines.

### Group

Groups content so it either fits on one line or breaks consistently:

```
group;                                    // Group entire rule
group from "(" to ")";                    // Group content in parens
group from after "(" to before ")";       // Exclude parens from group
group to ";";                             // Group from start to semicolon
```

### Nest

Indent content when lines break:

```
nest;                                     // Nest entire rule (indent=1)
nest 2;                                   // Nest with indent=2
nest from after ":=" to ";";              // Nest body of rule definition
nest from after "(" to before ")";        // Nest content in parens
```

Token content is never re-indented. A token that starts a line takes the nest indent once,
before its first character; a token that spans lines — a multi-line string, a block comment —
keeps every later line exactly as written. Only layout breaks (`hard`, `blank`, a broken `bsp` or
`soft`) start an indented line, and the one grammar token that is a layout break is the exact
literal `"\n"`. So a line-comment rule whose terminator sits inside the comment regex
(`/\/\/[^\n]*\n/`) gets no layout break from it, and the token after the comment lands at column
0: end the rule in a literal `"\n"` instead, as `fegen.fltkg` does. A `"\r\n"` terminator is
token bytes, not a layout break.

A preserved comment in a nest's first or last gap — the gap after its opening delimiter or
before its closing one — is indented with the nest's content, exactly like a comment between
the nest's items, and the gap renders the source's whitespace around the comment and nothing
else: a delimiter after an own-line comment starts its own line at the enclosing indent, and a
delimiter the source put on the comment's line stays there, whether or not the enclosing group
breaks. Whatever an interior comment does to a layout, a boundary comment does too: a `group`
that wraps the nest contains the comment and breaks on it, as it would on a comment between
items. A `group` declared inside the nest — `nest` before `group` over the same anchors, or a
`group` on a narrower range — does not contain the comment and its body may stay flat.

### Join

Join items with a separator:

```
join from items to end bsp;               // Join with breaking space
```

A `text("…")` doc literal is verbatim bytes, including any `\n` inside it, and the line after its
own newline never takes the nest indent; a separator that breaks the line is `hard` or
`concat([text(","), hard])`.

## Item Disposition

### Omit

Completely remove an item from output:

```
omit trailing_comma;          // Remove item labeled "trailing_comma"
```

### Render

Replace an item with specific content:

```
render ";" as hard;           // Replace semicolon with newline
render separator as nbsp;     // Replace separator with space
```

## Complete Example

Here's a complete format spec for FLTK grammar files:

```
// Preserve comments, and up to one blank line between logical groups
trivia_preserve: LineComment, BlockComment;
preserve_blanks: 1;

// Default spacing
ws_allowed: nil;
ws_required: bsp;

// Punctuation spacing
before ";" { nbsp; }
after ";" { hard; }
before "," { nbsp; }
after "," { bsp; }

// Rule definitions
rule rule
{
    group to ";";
    nest from after ":=" to ";";
    after name { nbsp; }
    after ":=" { bsp; }
}

// Alternatives formatting
rule alternatives
{
    group;
    before "|" { bsp; }
    after "|" { nbsp; }
}

// Parenthesized expressions
rule term
{
    group;
    after "(" { bsp; }
    before ")" { bsp; }
    nest from after "(" to before ")";
}
```

## Usage

Format specs are used with the unparse CLI:

```bash
bazel run --run_under="cd $PWD &&" @fltk//:unparse_cli -- GRAMMAR FORMAT_SPEC INPUT_FILE -o OUTPUT_FILE
```

`--run_under="cd $PWD &&"` makes the relative paths after `--` resolve in the directory you
invoked Bazel from rather than in the runfiles tree; see [usage.md](usage.md#quick-start-source-generation).

Or programmatically:

```python
from fltk.plumbing import (
    parse_grammar_file,
    parse_format_config_file,
    generate_parser,
    generate_unparser,
    parse_text,
    unparse_cst,
    render_doc,
)

grammar = parse_grammar_file("my.fltkg")
fmt_config = parse_format_config_file("my.fltkfmt")
parser_result = generate_parser(grammar, capture_trivia=True)
unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, formatter_config=fmt_config)

parse_result = parse_text(parser_result, source_code)
doc = unparse_cst(unparser_result, parse_result.cst, source_code)
output = render_doc(doc)
```
