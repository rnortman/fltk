# FLTK CST Structure Guide

This document explains how FLTK grammars map to Concrete Syntax Tree (CST) structures and how to work with the generated CST nodes.

## Overview

When FLTK parses input using your grammar, it produces a CST - a tree of nodes representing the parsed structure. Each grammar rule generates a corresponding Python class with typed accessor methods for navigating the tree.

## CST Node Structure

Every CST node class has these core attributes and methods:

### Core Attributes

```python
@dataclass
class RuleName:
    span: Span = UnknownSpan  # Source position (start, end)
    children: list[tuple[Optional[Label], ChildType]] = field(default_factory=list)
```

- **`span`**: A `Span(start, end)` indicating the byte range in the source text this node covers
- **`children`**: A list of `(label, child)` tuples where:
  - `label` is either a `Label` enum value or `None` for unlabeled items
  - `child` is either another CST node or a `Span` (for literals/regexes)

### Label Enum

Each node class has an inner `Label` enum with members for each labeled item in the rule:

```python
class RuleName:
    class Label(enum.Enum):
        LABEL_ONE = enum.auto()
        LABEL_TWO = enum.auto()
        # ... one for each labeled item
```

### Core Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `append(child, label=None)` | `None` | Add a child with optional label |
| `extend(children, label=None)` | `None` | Add multiple children |
| `child()` | `(label, child)` | Get the single child (raises if not exactly 1) |

### Label-Specific Methods

For each label in the rule, these methods are generated:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `append_{label}(child)` | `None` | Add child with this label |
| `extend_{label}(children)` | `None` | Add multiple children with this label |
| `children_{label}()` | `Iterator[ChildType]` | Iterate over children with this label |
| `child_{label}()` | `ChildType` | Get single child with this label (raises if not exactly 1) |
| `maybe_{label}()` | `Optional[ChildType]` | Get single child or `None` (raises if > 1) |

## How Grammar Constructs Map to CST

### Rule Names to Class Names

Rule names are converted to PascalCase class names:

| Grammar Rule | CST Class |
|--------------|-----------|
| `expr` | `Expr` |
| `if_statement` | `IfStatement` |
| `_trivia` | `Trivia` |

### Literals and Regexes → Span

Literals and regular expressions become `Span` objects in the CST, not separate nodes:

```fltkg
number := value:/[0-9]+/ ;
keyword := "if" ;
```

When parsed, both produce a `Span(start, end)` as the child, not a nested node.

**Example**: Parsing `"123"` with rule `number := value:/[0-9]+/`:

```python
# CST structure:
# fmt: off
Number(
    span=Span(0, 3),
    children=[(Number.Label.VALUE, Span(0, 3))]
)
# fmt: on

# Access the matched text:
span = number_node.child_value()  # Returns Span(0, 3)
source_text[span.start : span.end]  # Returns "123"
```

### Rule References → Nested Nodes with Default Labels

References to other rules create nested CST nodes. **Important**: Unlabeled rule references automatically get the rule name as their label:

```fltkg
expr := term ;
term := number ;
number := /[0-9]+/ ;
```

Parsing `"42"` produces:

```python
# fmt: off
Expr(
    children=[(Expr.Label.TERM, Term(
        children=[(Term.Label.NUMBER, Number(
            children=[(None, Span(0, 2))]
        ))]
    ))]
)
# fmt: on
```

The `term` reference gets label `TERM`, and `number` gets label `NUMBER` - derived from the rule names.

### Labels → Named Access

Labels create named accessors. You can use explicit labels or rely on the automatic labeling for rule references:

```fltkg
assignment := target:identifier , ":=" , value:expr ;
```

```python
# fmt: off
# Access by label:
assignment.child_target()   # Returns the Identifier node
assignment.child_value()    # Returns the Expr node
# fmt: on

# Iterate children with specific label:
for child in node.children_target():
    ...
```

### Default Dispositions

When no disposition (`%`, `$`, `!`) is specified:

- **Rule references**: `INCLUDE` (they get a default label, so they're included)
- **Sub-expressions `(...)`**: `INCLUDE`
- **Unlabeled literals/regexes**: `SUPPRESS` (not in CST!)

This means:

```fltkg
rule := "keyword" , identifier , ";" ;
```

The `"keyword"` and `";"` literals are **suppressed by default** because they have no labels. Only `identifier` appears in the CST (with label `IDENTIFIER`).

To include a literal in the CST, add a label:

```fltkg
rule := kw:"keyword" , identifier , semi:";" ;
```

### Unlabeled Literals → Suppressed by Default

Unlabeled literals and regexes are suppressed (not in CST) by default:

```fltkg
parens := "(" , expr , ")" ;
```

```python
# Only expr is in the CST (parentheses are suppressed):
# fmt: off
Parens(
    children=[(Parens.Label.EXPR, Expr(...))]
)
# fmt: on

# To include parentheses, add labels:
# parens := open:"(" , expr , close:")" ;
```

### Alternatives → Same Node Type

All alternatives of a rule produce the same node type:

```fltkg
factor := number | "(" , expr , ")" ;
```

Both `123` and `(1+2)` produce a `Factor` node, but with different children.

### Quantifiers → Multiple or Optional Children

Quantifiers affect how many children of that type appear:

#### Required (no quantifier) - Exactly One

```fltkg
rule := name:identifier ;
```

```python
node.child_name()  # Returns exactly one, raises if not
```

#### Optional (`?`) - Zero or One

```fltkg
rule := name:identifier , (":" , type:identifier)? ;
```

```python
node.maybe_type()  # Returns the type or None
# OR check explicitly:
list(node.children_type())  # Returns [] or [child]
```

#### One or More (`+`) - At Least One

```fltkg
rule := items:item+ ;
```

```python
node.child_items()  # Returns first item, raises if none
list(node.children_items())  # Returns list of all items (at least 1)
```

#### Zero or More (`*`) - Any Number

```fltkg
rule := items:item* ;
```

```python
list(node.children_items())  # Returns list of items (possibly empty)
```

### Sub-expressions (Parentheses) → Flattened into Parent

Parenthesized sub-expressions in the grammar do NOT create separate nodes. Their children are added directly to the parent:

```fltkg
expr := term , ("+" , term)* ;
```

Parsing `"1+2+3"` produces:

```python
Expr(
    children=[
        (None, Term(...)),  # "1"
        (None, Span(...)),  # "+"
        (None, Term(...)),  # "2"
        (None, Span(...)),  # "+"
        (None, Term(...)),  # "3"
    ]
)
```

Note: The parentheses `("+" , term)*` don't create a separate node - each `+` and `term` is added directly to `Expr`.

### Suppressed Items (`%`) → Not in CST

Suppressed items are parsed but excluded from the CST:

```fltkg
list := "[" , item , (%"," , item)* , "]" ;
```

```python
# Brackets and commas are NOT in children:
List(
    children=[
        (None, Item(...)),  # first item
        (None, Item(...)),  # second item
        # No commas or brackets!
    ]
)
```

To get the source text of suppressed items, use the `span` to read from the original source.

### Included Items (`$`) → Explicitly Included

The `$` disposition is the default behavior - item is included in CST:

```fltkg
rule := $name:identifier ;  # Same as: name:identifier
```

### Inlined Items (`!`) → Children Merged into Parent

Inline disposition merges a rule's children directly into the parent:

```fltkg
wrapper := !inner ;
inner := a:item , b:item ;
```

Without `!`:
```python
Wrapper(children=[(None, Inner(children=[...]))])
```

With `!`:
```python
# fmt: off
Wrapper(children=[
    (Wrapper.Label.A, Item(...)),
    (Wrapper.Label.B, Item(...)),
])
# fmt: on
```

**Note**: Inline has limited support and may raise `NotImplementedError`.

## Trivia Handling

### What is Trivia?

Trivia is whitespace and comments defined by the `_trivia` rule. How it appears in the CST depends on the `capture_trivia` setting.

### With `capture_trivia=True`

Trivia nodes appear in the CST between other children:

```fltkg
statement := first:"hello" , second:"world" ;
_trivia := /\s+/ ;
```

Parsing `"hello   world"`:

```python
# fmt: off
Statement(
    children=[
        (Statement.Label.FIRST, Span(0, 5)),   # "hello"
        (None, Trivia(...)),                   # whitespace "   "
        (Statement.Label.SECOND, Span(8, 13)), # "world"
    ]
)
# fmt: on
```

### With `capture_trivia=False` (Default)

Trivia is parsed but not included in the CST:

```python
# fmt: off
Statement(
    children=[
        (Statement.Label.FIRST, Span(0, 5)),   # "hello"
        (Statement.Label.SECOND, Span(8, 13)), # "world"
        # No trivia node
    ]
)
# fmt: on
```

### Complex Trivia Structure

If your `_trivia` rule has structure (labels, nested rules), the Trivia node captures that structure:

```fltkg
_trivia := (line_comment | whitespace)+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . "\n" ;
whitespace := /\s+/ ;
```

## Complete Example

### Grammar

```fltkg
expr := term , (op:("+" | "-") , term)* ;
term := factor , (op:("*" | "/") , factor)* ;
factor := num:number | "(" , inner:expr , ")" ;
number := value:/[0-9]+/ ;
```

### Input

```
1 + 2 * 3
```

### Resulting CST (with trivia capture)

```python
# fmt: off
Expr(
    span=Span(0, 9),
    children=[
        (Expr.Label.TERM, Term(
            span=Span(0, 1),
            children=[
                (Term.Label.FACTOR, Factor(
                    children=[(Factor.Label.NUM, Number(
                        children=[(Number.Label.VALUE, Span(0, 1))]
                    ))]
                ))
            ]
        )),
        (None, Trivia(span=Span(1, 2))),  # space
        (Expr.Label.OP, Span(2, 3)),      # "+"
        (None, Trivia(span=Span(3, 4))),  # space
        (Expr.Label.TERM, Term(
            span=Span(4, 9),
            children=[
                (Term.Label.FACTOR, Factor(
                    children=[(Factor.Label.NUM, Number(
                        children=[(Number.Label.VALUE, Span(4, 5))]
                    ))]
                )),
                (None, Trivia(span=Span(5, 6))),  # space
                (Term.Label.OP, Span(6, 7)),      # "*"
                (None, Trivia(span=Span(7, 8))),  # space
                (Term.Label.FACTOR, Factor(
                    children=[(Factor.Label.NUM, Number(
                        children=[(Number.Label.VALUE, Span(8, 9))]
                    ))]
                ))
            ]
        ))
    ]
)
# fmt: on
```

### Accessing the CST

```python
# Get all operators in expr (using the label)
ops = list(expr.children_op())  # [Span(2, 3)]  - just "+"

# Get all terms (using the auto-derived label)
terms = list(expr.children_term())  # [Term(...), Term(...)]


# Get the actual text for a span
def get_text(span: Span, source: str) -> str:
    return source[span.start : span.end]


# Navigate to number values
for label, child in expr.children:
    if isinstance(child, Term):
        for _, factor_child in child.children:
            if isinstance(factor_child, Factor):
                num = factor_child.maybe_num()
                if num:
                    value_span = num.child_value()
                    print(get_text(value_span, source))
```

## Working with CST in Practice

### Getting Source Text

```python
from fltk.fegen.pyrt.terminalsrc import Span


def get_text(node_or_span, source: str) -> str:
    """Get source text for a node or span."""
    if isinstance(node_or_span, Span):
        return source[node_or_span.start : node_or_span.end]
    return source[node_or_span.span.start : node_or_span.span.end]
```

### Traversing the Tree

```python
def visit_all(node, visitor_fn):
    """Visit all nodes in the tree."""
    visitor_fn(node)
    if hasattr(node, "children"):
        for label, child in node.children:
            if hasattr(child, "children"):  # It's a node, not a Span
                visit_all(child, visitor_fn)
```

### Finding Specific Node Types

```python
def find_all(node, node_type):
    """Find all nodes of a specific type."""
    results = []

    def collector(n):
        if isinstance(n, node_type):
            results.append(n)

    visit_all(node, collector)
    return results
```

### Type-Safe Access Pattern

```python
# Safe access to optional children
if type_node := assignment.maybe_type():
    # type is present
    process_type(type_node)

# Safe access to repeated children
for item in container.children_items():
    process_item(item)

# Ensure exactly one child exists
try:
    required_child = node.child_name()
except ValueError:
    # Handle missing or multiple children
    pass
```

## Summary: Grammar to CST Mapping

| Grammar Construct | CST Representation |
|-------------------|-------------------|
| Rule `foo := ...` | Class `Foo` with children list |
| Literal `"text"` (labeled) | `Span(start, end)` with label |
| Literal `"text"` (unlabeled) | **Suppressed** - not in CST |
| Regex `/pattern/` (labeled) | `Span(start, end)` with label |
| Regex `/pattern/` (unlabeled) | **Suppressed** - not in CST |
| Rule reference `other` | Nested `Other` node with label `OTHER` (auto-derived) |
| Explicit label `name:term` | Child with `Label.NAME` |
| `%` (suppress) | Not in CST |
| `$` (include) | In CST |
| `!` (inline) | Children merged into parent |
| `?` (optional) | 0 or 1 children |
| `+` (one or more) | 1+ children |
| `*` (zero or more) | 0+ children |
| Sub-expression `(...)` | Children flattened into parent |
| Alternatives `a \| b` | Same node type, different children |
| Trivia (if captured) | `Trivia` nodes between children (label=None) |
