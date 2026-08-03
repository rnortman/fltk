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

Alongside these, each node class gets a smaller set of accessors shaped by what the grammar
actually guarantees — see [Ergonomic Accessors](#ergonomic-accessors).

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

The inlined rule's labels join the parent's `Label` enum and child-type union, and any
trivia captured between the inlined rule's items attaches to the **parent** as an unlabeled
child. The inlined rule itself is unaffected: it still has its own node class, parser entry
point and entry in `RULE_NAMES`, and behaves normally wherever it is referenced without `!`.

#### Rules for `!`

- **Rule references only.** `!"lit"`, `!/re/` and `!( ... )` are errors — there are no
  children to splice.
- **No label.** `x:!inner` is an error: the inlined rule contributes no node for the label
  to name. An unlabeled `!inner` also does *not* get the implicit `inner` label that a plain
  `inner` reference would.
- **No trivia targets.** `!_trivia`, or `!` of any rule reachable from `_trivia`, is an
  error. This includes using `!` inside the trivia subtree (`_trivia := !ws`).
- **No `!` cycles.** `a := !b ; b := !a ;` is an error. Ordinary recursion is unaffected —
  a rule referenced normally inside an inlined body is fine.
- **Quantifiers apply to the whole body.** `!inner?` splices zero or one copy of `inner`'s
  children; `!inner*` splices any number, in source order.

#### Consequences to expect

- The call site loses `inner`'s packrat memoization and terminal failures inside the spliced
  body are attributed to the parent rule — the same behavior as writing the body out as a
  sub-expression by hand.
- `.fltkfmt` rule configs attach to nodes by rule, and inlined content lives in the parent
  node, so the **parent** rule's config governs it. A `rule inner { ... }` block no longer
  applies at `!inner` sites; it still applies wherever `inner` is referenced normally.

## Ergonomic Accessors

The five label-specific methods above are uniform: every label gets all of them, whatever
the grammar says about how many children can carry that label. On top of them, generated
node classes carry a second, smaller surface derived from the grammar's own guarantees.
These members are additive — nothing in the five-method set changes — and they are emitted
identically by the Python and Rust backends.

### Bare per-label accessors

For a label `foo`, the generated class gets a `foo()` method whose type follows the label's
multiplicity over the **whole rule** (all alternatives combined):

| Multiplicity | Python | Rust (native) |
|---|---|---|
| exactly one | `foo() -> T` (raises unless exactly one) | `fn foo(&self) -> &T` |
| at most one | `foo() -> T \| None` (raises if more than one) | `fn foo(&self) -> Option<&T>` |
| anything else | `foo() -> list[T]` | `fn foo(&self) -> impl Iterator<Item = &T>` |

```fltkg
decl := name:identifier , (":" , type:identifier)? ;
args := arg:expr* ;
```

```python
decl.name()  # -> Identifier      (required by every alternative)
decl.type()  # -> Identifier|None (present in only some parses)
args.arg()  # -> list[Expr]
```

A label that is required *twice* in one alternative, or that appears under a `+`/`*`
quantifier, is a collection — the accessor never claims a guarantee the parser does not
make.

### Text shortcuts

`{label}_text()` is emitted when the label's only possible child type is a `Span` (a
literal or regex) and the label is single-valued. It replaces the two-hop
`node.child_foo()` + span-to-text dance:

```python
number.value_text()  # -> str        (required label)
suffix.unit_text()  # -> str | None (optional label; None when the child is absent)
```

`text()` is emitted on **terminal-only** rules — rules whose children are all spans — and
returns the node's own span text. Note that a node's span covers suppressed content too:

```fltkg
string_literal := %"\"" . content:/[^"]*/ . %"\"" ;
```

```python
lit.text()  # '"hello"'  — the node span, quotes included
lit.content_text()  # 'hello'    — the labeled span only
```

### `variant()`

`variant()` is emitted on rules that are pure dispatch: two or more alternatives, each of
which is exactly one required, labeled item. It returns the `Label` of the node's sole
labeled child, so a `match` replaces a chain of `maybe_*` probes:

```fltkg
statement := assign:assignment | call:call_expr | ret:return_stmt ;
```

```python
match statement.variant():
    case Statement.Label.ASSIGN:
        ...
    case Statement.Label.CALL:
        ...
```

Because unlabeled rule references get the rule name as an implicit label, this covers plain
`a := b | c | d ;` dispatch rules too. `Label` values compare equal across the Python and
Rust backends, so `variant()` results are interchangeable.

### Name collisions: skipped, never renamed

These members put label names directly into the class namespace, so a label can collide
with something that is already there. When that happens the **new** member is dropped and
the existing surface wins; generation logs the rule, member and reason, and never fails.
A candidate is skipped when its name:

- is a fixed member of the node class (`span`, `kind`, `children`, `child`, `append`,
  `text`, `variant`, ...),
- is already claimed by another label's five-method set (label `x` and label `append_x`
  together: `append_x`'s bare accessor loses, because `x`'s `append_x()` was claimed first),
- starts with `__` (Python name mangling would rewrite it, and dunders would shadow the
  dataclass's own),
- is a Python keyword, or one of the Rust keywords that cannot be written as a raw
  identifier (`crate`, `self`, `super`, `Self`, `_`).

Other Rust keywords are fine: a label named `type` becomes `r#type()` on the Rust native
surface and keeps the name `type()` in Python.

The routine case is a label that shadows a rule-level member. In
`identifier := text:/[a-z]+/ ;`, the label `text` loses its bare accessor to the rule-level
`text()`, and `text_text()` is emitted for the labeled span — so `identifier.text()` still
returns the string you wanted.

Candidates are claimed in a fixed order (`text`, `variant`, then per label in sorted order
the bare accessor followed by its text shortcut), so the outcome is deterministic and the
same on both backends.

### Errors, and the Rust native panic contract

Everything reachable from Python — the Python backend's classes and the Rust backend's
Python bindings alike — raises `ValueError` on a violated expectation, with the same
message the corresponding `child_*`/`maybe_*` method would produce. `*_text()` and `text()`
raise if the span carries no source, which only happens for hand-built nodes; storing a
non-`Span` child under a span label (only possible through the untyped `append`/`extend`)
makes `*_text()` raise `TypeError` naming the label.

Two error wordings are backend-specific rather than shared: the `maybe_*` count message for
a duplicated child, and the message for a span whose indices are out of range for its
source. Both come from surfaces that predate these members and that the new members report
verbatim; match on the exception type, not the message text, if you switch backends.

The Rust **native** surface is different, deliberately. `child_foo()` and friends return
`Result<_, CstError>` and never panic; the ergonomic accessors return the value directly
and **panic** when the tree violates what the grammar guarantees — the wrong child count,
or a sourceless span. Only hand construction or hand mutation can produce such a tree; a
parser-produced one cannot. Reach for the checked five-method set in code that builds or
mutates trees, and for the ergonomic accessors when consuming a parse result.

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
