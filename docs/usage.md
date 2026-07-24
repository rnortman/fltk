# FLTK Usage Guide

This guide explains how to use FLTK to parse text using your grammar.

## Two Ways to Use FLTK

FLTK offers two approaches:

1. **In-memory generation** - Generate parser at runtime, good for development and dynamic grammars
2. **Source file generation** - Generate `.py` files to commit to your project, good for production

## Quick Start (In-Memory)

For rapid development, generate the parser at runtime:

```python
from fltk.plumbing import parse_grammar, generate_parser, parse_text

# 1. Define your grammar
grammar_text = """
expr := term , ("+" , term)* ;
term := factor , ("*" , factor)* ;
factor := num:number | "(" , inner:expr , ")" ;
number := value:/[0-9]+/ ;
"""

# 2. Parse the grammar and generate a parser
grammar = parse_grammar(grammar_text)
parser_result = generate_parser(grammar)

# 3. Parse some input text
result = parse_text(parser_result, "1 + 2 * 3", "expr")

if result.success:
    cst = result.cst  # The parsed CST
    print("Parse succeeded!")
else:
    print(f"Parse failed: {result.error_message}")
```

## Quick Start (Source Generation)

For production use, generate Python source files that you can commit to your project:

**1. Create a grammar file** (`calc.fltkg`):
```
expr := term , ("+" , term)* ;
term := factor , ("*" , factor)* ;
factor := num:number | "(" , inner:expr , ")" ;
number := value:/[0-9]+/ ;
```

**2. Generate parser source files:**
```bash
uv run python -m fltk.fegen.genparser calc.fltkg calc calc_cst -v
```

This generates:
- `calc_cst.py` - CST node classes
- `calc_parser.py` - Parser without trivia capture
- `calc_trivia_parser.py` - Parser with trivia capture

**3. Use the generated parser:**
```python
from calc_cst import Expr, Term, Factor, Number
from calc_trivia_parser import Parser
from fltk.fegen.pyrt.terminalsrc import TerminalSource

# Parse input
source = TerminalSource("1 + 2 * 3")
parser = Parser(source)
result = parser.apply__parse_expr(0)

if result and result.pos == len(source.terminals):
    cst = result.result  # Expr node
    print("Parse succeeded!")
else:
    print("Parse failed")
```

### CLI Options

```bash
# Generate both parser variants (default)
uv run python -m fltk.fegen.genparser grammar.fltkg mylang mylang_cst

# Generate only trivia-preserving parser (for formatters)
uv run python -m fltk.fegen.genparser grammar.fltkg mylang mylang_cst --trivia-only

# Generate only non-trivia parser (for compilers)
uv run python -m fltk.fegen.genparser grammar.fltkg mylang mylang_cst --no-trivia-only

# Specify output directory
uv run python -m fltk.fegen.genparser grammar.fltkg mylang mylang_cst -o output/

# Verbose output
uv run python -m fltk.fegen.genparser grammar.fltkg mylang mylang_cst -v
```

| Argument | Description |
|----------|-------------|
| `GRAMMAR_FILE` | Path to the `.fltkg` grammar file |
| `BASE_NAME` | Base name for output files (e.g., `calc` produces `calc_cst.py`) |
| `CST_MODULE_NAME` | Python import path for CST module (e.g., `calc_cst` or `myproject.calc_cst`) |

### Bazel Integration

For Bazel-based projects, add FLTK as a dependency and use the `generate_parser` rule.

**1. Add FLTK to your `MODULE.bazel`:**
```python
bazel_dep(name="fltk", version="...")  # or use git_override
```

**2. Use the rule in your `BUILD.bazel`:**
```python
load("@fltk//:rules.bzl", "generate_parser")

generate_parser(
    name="calc_parser_gen",
    src="calc.fltkg",
    base_name="calc",
    cst_mod_path="myproject.calc_cst",
)

py_library(
    name="calc_parser",
    srcs=[
        ":calc_parser_gen",  # Generates calc_cst.py, calc_parser.py, calc_trivia_parser.py
    ],
    deps=["@fltk//:fltk"],
)
```

Rule attributes:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `src` | label | Yes | The `.fltkg` grammar file |
| `base_name` | string | Yes | Base name for output files |
| `cst_mod_path` | string | Yes | Module import path for CST classes |
| `trivia_only` | bool | No | Generate only trivia-preserving parser |
| `no_trivia_only` | bool | No | Generate only non-trivia parser |

See the FLTK repository's `BUILD.bazel` for more examples.

## Step-by-Step Guide (In-Memory)

### Step 1: Define Your Grammar

Write your grammar using the FLTK grammar syntax. See [grammar-syntax.md](grammar-syntax.md) for the complete reference.

```python
grammar_text = """
statement := assignment | expr ;
assignment := name:identifier , ":=" , value:expr , ";" ;
expr := term , (op:("+" | "-") , term)* ;
term := factor , (op:("*" | "/") , factor)* ;
factor := num:number | "(" , inner:expr , ")" | var:identifier ;
number := value:/[0-9]+/ ;
identifier := name:/[a-z][a-z0-9]*/ ;
"""
```

Or load from a file:

```python
from fltk.plumbing import parse_grammar_file
from pathlib import Path

grammar = parse_grammar_file(Path("my_grammar.fltkg"))
```

### Step 2: Parse the Grammar

Convert your grammar text into FLTK's Grammar Semantic Model (GSM):

```python
from fltk.plumbing import parse_grammar

grammar = parse_grammar(grammar_text)

# Inspect the grammar
print(f"Rules: {[rule.name for rule in grammar.rules]}")
# Output: Rules: ['statement', 'assignment', 'expr', 'term', 'factor', 'number', 'identifier']
```

If the grammar has syntax errors, `parse_grammar` raises `ValueError` with a detailed error message.

### Step 3: Generate a Parser

Generate a parser from the grammar:

```python
from fltk.plumbing import generate_parser

parser_result = generate_parser(grammar, capture_trivia=True)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grammar` | `Grammar` | required | The parsed grammar |
| `capture_trivia` | `bool` | `True` | Include whitespace/comments in CST |

**Returns:** `ParserResult` with these attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `parser_class` | `type` | The generated parser class |
| `cst_module` | `module` | Module containing CST node classes |
| `cst_module_name` | `str` | Name of the CST module |
| `grammar` | `Grammar` | The enhanced grammar (with trivia rules) |
| `capture_trivia` | `bool` | Whether trivia capture is enabled |

### Step 4: Parse Text

Parse input text using the generated parser:

```python
from fltk.plumbing import parse_text

result = parse_text(parser_result, "x := 1 + 2;", "statement")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `parser_result` | `ParserResult` | required | Result from `generate_parser()` |
| `text` | `str` | required | The input text to parse |
| `rule_name` | `str \| None` | `None` | Start rule (defaults to first rule) |

**Returns:** `ParseResult` with these attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `cst` | `Node \| None` | The parsed CST (None if failed) |
| `terminals` | `str` | The original input text |
| `success` | `bool` | Whether parsing succeeded |
| `error_message` | `str \| None` | Error details if parsing failed |

### Step 5: Work with the CST

See [cst-structure.md](cst-structure.md) for detailed CST documentation.

```python
if result.success:
    cst = result.cst
    source = result.terminals

    # Get source text for a span
    def get_text(span):
        return source[span.start : span.end]

    # Access labeled children
    if hasattr(cst, "child_name"):
        name_span = cst.child_name()
        print(f"Name: {get_text(name_span)}")

    # Iterate over children
    for label, child in cst.children:
        print(f"Label: {label}, Child: {child}")
```

## Complete Example

```python
from fltk.plumbing import parse_grammar, generate_parser, parse_text

# Define a simple calculator grammar
grammar_text = """
expr := term , (op:("+" | "-") , term)* ;
term := factor , (op:("*" | "/") , factor)* ;
factor := num:number | "(" , inner:expr , ")" ;
number := value:/[0-9]+/ ;
"""

# Parse grammar and generate parser
grammar = parse_grammar(grammar_text)
parser_result = generate_parser(grammar)

# Parse an expression
result = parse_text(parser_result, "1 + 2 * (3 + 4)", "expr")

if not result.success:
    print(f"Parse error: {result.error_message}")
    exit(1)


# Walk the CST to evaluate the expression
def evaluate(node, source):
    """Recursively evaluate the expression CST."""
    class_name = node.__class__.__name__

    if class_name == "Number":
        span = node.child_value()
        return int(source[span.start : span.end])

    elif class_name == "Factor":
        # Factor is either num:number or inner:expr
        if num := node.maybe_num():
            return evaluate(num, source)
        if inner := node.maybe_inner():
            return evaluate(inner, source)

    elif class_name == "Term":
        # term := factor , (op:("*" | "/") , factor)*
        factors = list(node.children_factor())
        ops = list(node.children_op())

        result = evaluate(factors[0], source)
        for i, op_span in enumerate(ops):
            op = source[op_span.start : op_span.end]
            next_val = evaluate(factors[i + 1], source)
            if op == "*":
                result *= next_val
            else:
                result //= next_val
        return result

    elif class_name == "Expr":
        # expr := term , (op:("+" | "-") , term)*
        terms = list(node.children_term())
        ops = list(node.children_op())

        result = evaluate(terms[0], source)
        for i, op_span in enumerate(ops):
            op = source[op_span.start : op_span.end]
            next_val = evaluate(terms[i + 1], source)
            if op == "+":
                result += next_val
            else:
                result -= next_val
        return result

    raise ValueError(f"Unknown node type: {class_name}")


# Evaluate and print result
value = evaluate(result.cst, result.terminals)
print(f"Result: {value}")  # Output: Result: 15
```

## Error Handling

### Grammar Parse Errors

```python
try:
    grammar = parse_grammar("invalid grammar !!!")
except ValueError as e:
    print(f"Grammar error:\n{e}")
```

### Parse Errors

```python
result = parse_text(parser_result, "1 + + 2", "expr")  # Invalid input

if not result.success:
    print(f"Parse failed at:\n{result.error_message}")
    # Shows line/column and expected tokens
```

### Invalid Rule Name

```python
result = parse_text(parser_result, "1 + 2", "nonexistent_rule")

if not result.success:
    print(result.error_message)
    # "No parse method for rule 'nonexistent_rule'"
```

## Advanced: Trivia Capture

Control whether whitespace and comments appear in the CST:

```python
# With trivia capture (default) - whitespace nodes in CST
parser_with_trivia = generate_parser(grammar, capture_trivia=True)

# Without trivia capture - smaller, faster CST
parser_without_trivia = generate_parser(grammar, capture_trivia=False)
```

With `capture_trivia=True`, whitespace appears as `Trivia` nodes between other children. This is useful for:
- Code formatters (preserving whitespace)
- Language servers (accurate source positions)
- Linters (comment-based directives)

With `capture_trivia=False`, whitespace is parsed but not stored in the CST. This is useful for:
- Compilers (only care about structure)
- Interpreters (faster parsing)

See [trivia-guide.md](trivia-guide.md) for more details.

## Advanced: Low-Level Parser Access

For more control, you can use the generated parser class directly:

```python
from fltk.fegen.pyrt.terminalsrc import TerminalSource

# Get the parser class and CST module
parser_class = parser_result.parser_class
cst_module = parser_result.cst_module

# Create terminal source
source = TerminalSource("1 + 2 * 3")

# Create parser instance
parser = parser_class(source)

# Call parse method directly (returns ApplyResult or None)
apply_result = parser.apply__parse_expr(0)  # Start at position 0

if apply_result is not None:
    cst = apply_result.result  # The CST node
    end_pos = apply_result.pos  # Position after match

    # Check if we consumed all input
    if end_pos == len(source.terminals):
        print("Full parse succeeded!")
    else:
        print(f"Partial parse: stopped at position {end_pos}")
else:
    print("Parse failed")
```

## Unparsing (CST to Text)

FLTK can also convert a CST back to formatted text:

```python
from fltk.plumbing import generate_unparser, unparse_cst, render_doc

# Generate unparser (requires capture_trivia=True parser)
unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

# Convert CST to Doc (formatting combinators)
doc = unparse_cst(unparser_result, result.cst, result.terminals, "expr")

# Render Doc to string
output = render_doc(doc)
print(output)  # "1 + 2 * (3 + 4)"
```

## Formatting Files (CLI)

FLTK includes a CLI tool for parsing and formatting files using a grammar and format specification:

```bash
uv run python -m fltk.unparse_cli GRAMMAR FORMAT_SPEC INPUT_FILE [OPTIONS]
```

### Formatting FLTK Grammar Files

FLTK includes a formatter for `.fltkg` grammar files:

```bash
# Format a grammar file (output to stdout)
uv run python -m fltk.unparse_cli \
    fltk/fegen/fegen.fltkg \
    fltk/fegen/fegen.fltkfmt \
    mygrammar.fltkg

# Format in place
uv run python -m fltk.unparse_cli \
    fltk/fegen/fegen.fltkg \
    fltk/fegen/fegen.fltkfmt \
    mygrammar.fltkg \
    -o mygrammar.fltkg
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-o`, `--output FILE` | Write output to file (default: stdout) |
| `-w`, `--width N` | Maximum line width (default: 80) |
| `-i`, `--indent N` | Indent spacing (default: 2) |
| `-r`, `--rule NAME` | Start rule name (default: first rule) |
| `--generate-unparser FILE` | Write generated unparser source to file |
| `--cst-module NAME` | CST module path (required with `--generate-unparser`) |

### Format Specification Files

Format specs (`.fltkfmt` files) control how the unparser formats output. See [Format Specification Files](format-specs.md) for complete documentation.

Example (`fegen.fltkfmt`):

```
trivia_preserve: LineComment, BlockComment;
preserve_blanks: 1;

ws_allowed: nil;
ws_required: bsp;

after ";" { hard; }
before "," { nbsp; }

rule rule {
    group to ";";
    nest from after ":=" to ";";
}
```

See the existing format specs in the repository for more examples:
- `fltk/fegen/fegen.fltkfmt` - Format spec for grammar files
- `fltk/unparse/toy.fltkfmt` - Simple example

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `parse_grammar(text)` | Parse grammar text to Grammar |
| `parse_grammar_file(path)` | Parse grammar file to Grammar |
| `generate_parser(grammar, capture_trivia=True)` | Generate parser from Grammar |
| `parse_text(parser_result, text, rule_name=None)` | Parse text using generated parser |
| `generate_unparser(grammar, cst_module_name, formatter_config=None)` | Generate unparser |
| `unparse_cst(unparser_result, cst, terminals, rule_name=None)` | Convert CST to Doc |
| `render_doc(doc, config=None)` | Render Doc to string |

### Imports

```python
from fltk.plumbing import (
    parse_grammar,
    parse_grammar_file,
    generate_parser,
    parse_text,
    generate_unparser,
    unparse_cst,
    render_doc,
)
```
