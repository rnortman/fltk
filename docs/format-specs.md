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

### Join

Join items with a separator:

```
join from items to end bsp;               // Join with breaking space
```

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
