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
- [AST Guide](docs/ast-guide.md) - Generated typed trees and the `.fltkast` shaping sidecar
- [Rust serde Guide](docs/rust-serde-guide.md) - Deserializing source text into your own `#[derive(Deserialize)]` types
- [Trivia Guide](docs/trivia-guide.md) - Handling whitespace and comments

## Architecture

### Core Components

- **`fltk.fegen`**: Grammar processing and parser generation
- **`fltk.iir`**: Intermediate representation and type system
- **`fltk.fegen.pyrt`**: Runtime support (memoization, error tracking)

## Development

### Setup

Bazel (through `bazelisk`, which honours `.bazelversion`) and a Rust toolchain from
<https://rustup.rs/>. Everything else — the Python interpreter, the third-party wheels, the
tools — comes from the build graph.

A few tests compile a throwaway crate with `cargo --offline`, so run `cargo fetch --locked`
once in a fresh clone to warm the registry cache.

### Testing
```bash
# Run all tests
bazel test //...

# Run one test file
bazel test //tests:test_span

# Run with coverage (add --combined_report=lcov for one report over the whole suite)
bazel coverage //...
```

### Linting and Formatting
```bash
# Check style and types: clippy, ruff check, ruff format --check, pyright
bazel build --config lint //...

# Format code and apply auto-fixes
make fix

# Everything the CI gate runs
make check
```

### Build
```bash
bazel build //...
```

### Running the CLIs
```bash
# Generate a parser from a grammar (see docs/usage.md)
bazel run --run_under="cd $PWD &&" //:genparser -- generate calc.fltkg calc calc_cst

# Format a file against a grammar + format spec
bazel run --run_under="cd $PWD &&" //:unparse_cli -- grammar.fltkg spec.fltkfmt input.txt

# Language server for fltk's own .fltkg / .fltkfmt / .fltklsp files (see docs/lsp.md)
bazel run //:grammar_lsp -- fltkg
```

`--run_under="cd $PWD &&"` makes relative path arguments resolve where you invoked Bazel
rather than in the runfiles tree.

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
4. Run `bazel build --config lint //...` to check style and types
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/rnortman/fltk/issues)
