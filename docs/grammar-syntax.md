# FLTK Grammar Syntax Reference

This document provides a complete reference for the FLTK grammar notation used in `.fltkg` files.

## Overview

FLTK grammars define parsing rules that generate Parsing Expression Grammar (PEG) parsers. Each grammar produces a type-safe Concrete Syntax Tree (CST) with accessor methods for navigating the parsed structure.

## File Format

Grammar files use the `.fltkg` extension and contain one or more rule definitions. The grammar format is self-hosting - the grammar parser itself is defined using this notation.

## Grammar Structure

A grammar consists of one or more rules:

```fltkg
grammar := , rule+;
```

The leading `,` allows optional whitespace before the first rule.

## Rule Definition

Rules are defined with the `:=` operator and terminated with `;`:

```fltkg
rule_name := alternatives ;
```

Example:

```fltkg
expression := term , ("+" , term)* ;
number := /[0-9]+/ ;
```

### Rule Naming

Rule names must:
- Start with a lowercase letter or underscore
- Contain only lowercase letters, digits, and underscores
- Match the pattern: `/[_a-z][_a-z0-9]*/`

Valid: `expr`, `_trivia`, `rule_name`, `item2`
Invalid: `Expr`, `2rule`, `rule-name`

## Alternatives

Alternatives are separated by `|`:

```fltkg
factor := number | "(" , expr , ")" ;
```

The parser tries each alternative in order, succeeding with the first match (PEG ordered choice).

## Items and Sequences

An alternative contains a sequence of items. Items can be separated by separators that control whitespace handling.

### Items Syntax

```fltkg
items := separator? item (separator item)* separator?
```

Each item consists of:

```
[label:] [disposition] term [quantifier]
```

Example:

```fltkg
item := (label:identifier . ":")? . disposition? . term . quantifier? ;
```

## Separators (Whitespace Control)

Separators control how whitespace (trivia) is handled between items. There are three types:

| Separator | Name | Whitespace Behavior |
|-----------|------|---------------------|
| `.` | NO_WS | No whitespace allowed |
| `,` | WS_ALLOWED | Whitespace optional |
| `:` | WS_REQUIRED | Whitespace required |

### Examples

```fltkg
// No whitespace between label and colon
item := (label:identifier . ":")? . term ;

// Whitespace allowed (typical for most grammar rules)
rule := name:identifier , ":=" , alternatives , ";" ;

// Whitespace required (e.g., between keywords)
decl := "public" : identifier : "{" , body , "}" ;
```

### Leading and Trailing Separators

Separators can appear at the start and end of a sequence:

```fltkg
// Leading comma allows optional whitespace before first item
grammar := , rule+ ;

// Trailing comma allows optional whitespace after last item
rule := name:identifier , ":=" , alternatives , ";" , ;
```

The leading separator controls whether whitespace is allowed/required before the first item in that alternative.

## Terms

Terms are the basic parsing elements. There are four types:

### 1. Literals

String literals match exact text:

```fltkg
":="
"keyword"
'single quotes also work'
```

Literals can contain escape sequences (`\\`, `\"`, `\'`, `\n`, `\t`, etc.).

### 2. Regular Expressions

Regexes are enclosed in forward slashes:

```fltkg
/[0-9]+/
/[_a-z][_a-z0-9]*/
/[^\n]*/
```

Regex syntax follows Python's `re` module. Forward slashes inside the regex must be escaped: `\/`.

### 3. Rule References (Identifiers)

Reference other rules by name:

```fltkg
expression := term , ("+" , term)* ;
term := factor , ("*" , factor)* ;
factor := number | "(" , expression , ")" ;  // references expression
```

### 4. Sub-expressions (Parentheses)

Group items and alternatives:

```fltkg
expr := term , ("+" , term)* ;
factor := number | "(" , expr , ")" ;
```

Sub-expressions can contain full alternatives:

```fltkg
operator := ("+" | "-" | "*" | "/") ;
```

## Labels

Labels name captured elements for type-safe access in the CST:

```fltkg
rule := name:identifier , ":=" , body:alternatives , ";" ;
```

Syntax: `label:term` (no space between label, colon, and term due to `.` separator)

Labels generate accessor methods in the CST node classes:
- `child_name()` - returns single child
- `children_name()` - returns list of children (for repeated items)

## Dispositions

Dispositions control how items are included in the CST:

| Symbol | Name | Behavior |
|--------|------|----------|
| `%` | SUPPRESS | Parse but exclude from CST |
| `$` | INCLUDE | Include in CST (default) |
| `!` | INLINE | Flatten children into parent |

### SUPPRESS (`%`)

Parse the element but don't include it in the CST. Useful for structural elements like punctuation:

```fltkg
list := "[" , item , (%"," , item)* , %"]" ;
```

### INCLUDE (`$`)

Explicitly include in CST. This is the default if no disposition is specified:

```fltkg
rule := $name:identifier ;  // Same as: name:identifier
```

### INLINE (`!`)

Merge the rule's children directly into the parent node. Only valid for rule references:

```fltkg
statement := !expression ;  // expression's children become statement's children
```

**Note**: Inline disposition has limited support and may raise `NotImplementedError` in some cases.

## Quantifiers

Quantifiers control repetition:

| Symbol | Name | Matches |
|--------|------|---------|
| (none) | REQUIRED | Exactly 1 |
| `?` | NOT_REQUIRED | 0 or 1 |
| `+` | ONE_OR_MORE | 1 or more |
| `*` | ZERO_OR_MORE | 0 or more |

### Examples

```fltkg
// Optional element
rule := name:identifier , (":" , type:identifier)? ;

// One or more
grammar := rule+ ;

// Zero or more
items := item* ;
```

### Repetition Constraints

Items with `+` or `*` must not be able to match empty strings. This prevents infinite loops:

```fltkg
// INVALID - regex can match empty string
items := /a*/+ ;  // Error: repeated item can match empty string

// VALID - regex requires at least one character
items := /a+/* ;  // OK
```

## Comments

### Line Comments

```fltkg
// This is a line comment
rule := item ;  // Comment at end of line
```

### Block Comments

```fltkg
/* This is a
   block comment */
rule := /* inline comment */ item ;
```

**Note**: Block comments cannot be nested.

## Trivia (Whitespace and Comments)

Trivia consists of non-semantic content (whitespace, comments) that separates tokens.

### The `_trivia` Rule

Define custom trivia handling with a rule named `_trivia`:

```fltkg
_trivia := (line_comment | whitespace | block_comment)+ ;

whitespace := /\s+/ ;
line_comment := "//" . /[^\n]*/ . "\n" ;
block_comment := "/*" . /[^*]*(?:\*(?!\/)[^*]*)*/ . "*/" ;
```

See [trivia-guide.md](trivia-guide.md) for detailed trivia documentation.

### Default Trivia

If no `_trivia` rule is defined, FLTK uses:

```fltkg
_trivia := /\s+/ ;
```

### Trivia Rule Constraints

1. The `_trivia` rule must not match empty strings
2. Non-trivia rules cannot reference trivia rules
3. All rules reachable from `_trivia` are automatically classified as trivia rules

## Complete Grammar Meta-Grammar

This is the grammar that defines FLTK grammars (from `fegen.fltkg`):

```fltkg
grammar := , rule+;
rule := name:identifier , ":=" , alternatives , ";" ,;
alternatives := items , ("|" , items , )* ;
items := (no_ws:"." | ws_allowed:"," | ws_required:":")? ,
    item , ((no_ws:"." | ws_allowed:"," | ws_required:":") , item ,)* ,
    (no_ws:"." | ws_allowed:"," | ws_required:":")? ,;
item := (label:identifier . ":")? . disposition? . term . quantifier? ,;
term := identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")";
disposition := suppress:"%" | include:"$" | inline:"!";
quantifier := optional:"?" | one_or_more:"+" | zero_or_more:"*";
identifier := name:/[_a-z][_a-z0-9]*/;
raw_string := value:/([^\/\n\\]|\\.)+/;
literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/;
_trivia := (line_comment | line_comment? : | block_comment)+;
line_comment := prefix:"//" . content:/[^\n]*/ . "\n";
block_comment := start:"/*" , content:/[^*]*(?:\*(?!\/)[^*]*)*/ . end:"*/";
```

## Practical Examples

### Simple Expression Grammar

```fltkg
expr := term , (plus:"+" , term)* ;
term := factor , (mult:"*" , factor)* ;
factor := number | "(" , expr , ")" ;
number := value:/[0-9]+/ ;
```

### JSON-like Grammar

```fltkg
value := object | array | string | number | bool | null ;

object := "{" , (pair , (%"," , pair)*)? , "}" ;
pair := key:string , %":" , value:value ;

array := "[" , (value , (%"," , value)*)? , "]" ;

string := /"[^"]*"/ ;
number := /-?[0-9]+(\.[0-9]+)?/ ;
bool := "true" | "false" ;
null := "null" ;
```

### Programming Language Statement

```fltkg
statement := if_stmt | while_stmt | assignment | expr_stmt ;

if_stmt := "if" : condition:expr , "then" : body:statement ,
           ("else" : else_body:statement)? ;

while_stmt := "while" : condition:expr , "do" : body:statement ;

assignment := target:identifier , %":=" , value:expr , %";" ;

expr_stmt := expr , %";" ;
```

## Error Messages

Common validation errors:

| Error | Cause | Fix |
|-------|-------|-----|
| "Repeated potentially-nil items found" | `+` or `*` on item that can match empty | Ensure repeated term always matches at least one character |
| "Trivia rule '_trivia' cannot match empty string" | `_trivia` can be nil | Ensure trivia rule matches at least one character |
| "Trivia separation violations" | Non-trivia rule references trivia rule | Keep trivia rules separate from content rules |

## Best Practices

1. **Use labels** for elements you need to access in the CST
2. **Suppress punctuation** (`%`) that's only structural
3. **Use `,` separator** as the default for readability
4. **Use `.` separator** only when tokens must be adjacent (e.g., `identifier.":"`)
5. **Use `:` separator** when whitespace naturally separates keywords
6. **Start grammars with `, rule+`** to allow leading whitespace in input
7. **End rules with `, ;`** to allow trailing whitespace
