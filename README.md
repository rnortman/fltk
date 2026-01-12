# FLTK - Formal Language ToolKit

A Python library for building Parsing Expression Grammer (PEG) parsers using a custom grammar notation.
FLTK generates packrat PEG parsers that produce type-safe Concrete Syntax Trees (CST).
The overall goal is to allow developers to specify the grammar intuitively without worrying about the details of the parsing algorithm.
A major secondary goal is to make the resulting syntax trees easy to work with and type-safe.

## Features

- **Custom Grammar Notation**: Define grammars using `.fltkg` format (the grammar parser is self-hosting)
- **Extensions for recursive grammars**: Supports left-recursive grammars automatically
- **Packrat Parsing**: Built-in memoization for efficient O(N) parsing
- **Type-Safe CST**: Generated node classes with typed child access methods
- **Source Tracking**: All nodes maintain spans to original source text
- **Python Code Generation**: Generates clean, readable Python parser code

## Quick Start

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

# 3. Parse input text
result = parse_text(parser_result, "3 + 4 * 2", "expr")

if result.success:
    print("Parsed successfully!")
    # result.cst contains the CST
    # result.terminals contains the source text
else:
    print(f"Parse error: {result.error_message}")
```

For complete usage documentation, see [docs/usage.md](docs/usage.md).

## Grammar Syntax

FLTK uses a powerful grammar notation. For complete documentation, see [docs/grammar-syntax.md](docs/grammar-syntax.md).

### Quick Reference

```
rule_name := alternative1 | alternative2 ;
```

**Separators** (whitespace control):
- `.` - No whitespace allowed
- `,` - Whitespace optional
- `:` - Whitespace required

**Quantifiers**:
- `?` - Optional (zero or one)
- `+` - One or more
- `*` - Zero or more

**Dispositions**:
- `%` - Suppress (exclude from CST)
- `$` - Include (default)
- `!` - Inline (flatten into parent)

**Labels and Terms**:
```
rule := label:identifier , "literal" , /regex_pattern/ ;
```

## Documentation

- [Usage Guide](docs/usage.md) - How to use FLTK to parse text
- [Grammar Syntax Reference](docs/grammar-syntax.md) - Complete reference for the `.fltkg` grammar notation
- [CST Structure Guide](docs/cst-structure.md) - How grammars map to Concrete Syntax Trees
- [Trivia Guide](docs/trivia-guide.md) - Handling whitespace and comments

## Architecture

### Core Components

- **`fltk.fegen`**: Grammar processing and parser generation
- **`fltk.iir`**: Intermediate representation and type system
- **`fltk.fegen.pyrt`**: Runtime support (memoization, error tracking)

## Development

### Setup
```bash
# Install dependencies
uv sync --group test --group lint
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run coverage run -m pytest && uv run coverage report
```

### Linting and Formatting
```bash
# Check style and types
uv run ruff check . && uv run pyright

# Format code
uv run ruff format .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Build
```bash
# Using setuptools
uv build

# Using Bazel
bazel build //...
```

## Examples

See the grammar files in `fltk/fegen/` for real-world examples:
- `bootstrap.fltkg` - Minimal grammar for bootstrapping
- `fegen.fltkg` - Full grammar definition
- `fltk.fltkg` - Extended grammar with advanced features

## Requirements

- Python 3.10+
- Dependencies: `astor`, `typer`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `uv run ruff check . && uv run pyright` to check style and types
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/rnortman/fltk/issues)
