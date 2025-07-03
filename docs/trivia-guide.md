# FLTK Trivia Guide

## Overview

FLTK supports automatic handling of "trivia" - non-semantic content like whitespace and comments that should be skipped during parsing but can optionally be preserved for tooling. This guide explains how to define and use trivia in your grammars.

## Basic Trivia Rule

Define trivia by creating a rule named `_TRIVIA` in your grammar:

```fltk
_TRIVIA := whitespace | line_comment | block_comment;

whitespace := /\s+/;
line_comment := "//" . /[^\n]*/ . "\n";
block_comment := "/*" . /.*?\*/ . "*/";
```

## How Trivia Works

1. **Automatic Detection**: FLTK automatically detects the `_TRIVIA` rule and classifies all rules reachable from it as trivia rules
2. **Separator Behavior**: Trivia is consumed at separators (`,` and `:`) but not at concatenation (`.`)
3. **Rule Classification**: Rules are classified as either trivia or non-trivia, preventing mixed usage

Within a trivia rule, separators `,` and `:` refer to simple whitespace, not complex trivia.
This prevents recursion, plus it would just be very confusing to try to write trivia rules otherwise.

## Separator Types

FLTK provides three separator types that control trivia consumption:

- `.` - No trivia allowed between elements
- `,` - Trivia allowed between elements  
- `:` - Trivia required between elements

Example:
```fltk
function := "function" : name:identifier : "(" , params , ")";
//                     ^                 ^     ^        ^
//                     |                 |     |        |
//                  required          required  optional  optional
```

## CST and Trivia Capture Modes

FLTK generates Trivia CST node types to hold trivia.
These are just like any other CST node type, meaning that if the trivia rules have complex structure, the Trivia CST sub-tree will capture that structure.
This allows trivia to be used by tooling for complex purposes, such as doc comments, linter pragmas, etc.
In effect, you can define a mini-language inside the main grammar's trivia for these purposes.

FLTK generates two different parsers for each grammar, one that records trivia nodes in the CST and one which omits them from the CST.
The one that omits trivia nodes will be slightly faster and use less memory.

## Built-in Fallback

If no `_TRIVIA` rule is defined, FLTK automatically uses a default whitespace-only trivia rule equivalent to:

```fltk
_TRIVIA := /\s+/;
```

## Common Use Cases

- **Compilers**: Use performance mode for faster parsing
- **Language servers**: Use full mode to preserve comments for documentation
- **Formatters**: Use full mode to maintain comment positioning
- **Linters**: Use full mode if linter suppressions or directives are present in comments
