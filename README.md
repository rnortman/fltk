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

### Basic Usage

1. **Define a grammar** (`calc.fltkg`):
```
grammar := expression;
expression := term , (("+" | "-") , term)*;
term := factor , (("*" | "/") , factor)*;
factor := number | "(" , expression , ")";
number := /[0-9]+/;
```

2. **Generate parser**:
```python
import fltk

# Generate parser from grammar
parser_code = fltk.generate_parser("calc.fltkg")
with open("calc_parser.py", "w") as f:
    f.write(parser_code)
```

3. **Use the parser**:
```python
from calc_parser import Parser
import fltk.fegen.pyrt.terminalsrc as ts

source = "3 + 4 * 2"
parser = Parser(ts.StringTerminalSource(source))
cst = parser.parse_grammar()
print(cst)  # Parsed CST with full source tracking
```

## Grammar Syntax

FLTK uses a powerful grammar notation with the following features:

### Basic Rules
```
rule_name := alternative1 | alternative2;
```

### Item Separators
- `.` - No whitespace allowed between items
- `,` - Whitespace allowed between items  
- `:` - Whitespace required between items

### Quantifiers
- `?` - Optional (zero or one)
- `+` - One or more
- `*` - Zero or more

### Dispositions
- `%` - Suppress (don't include in CST)
- `$` - Include (force include)
- `!` - Inline (flatten into parent)

### Labels and Literals
```
rule := label:identifier , "literal" , /regex_pattern/;
```

### Advanced Features
```
rule := method_call() | variable_ref;
invocation := method:identifier . "(" , args:expression? , ")";
```

## Architecture

### Core Components

- **`fltk.fegen`**: Grammar processing and parser generation
- **`fltk.iir`**: Intermediate representation and type system
- **`fltk.fegen.pyrt`**: Runtime support (memoization, error tracking)

## Development

### Testing
```bash
# Run all tests
hatch run test

# Run with coverage
hatch run cov
```

### Linting
```bash
# Check style and types
hatch run lint:all

# Format code
hatch run lint:fmt
```

### Build
```bash
# Using Hatch
hatch build

# Using Bazel
bazel build //...
```

## Examples

See the grammar files in `fltk/fegen/` for real-world examples:
- `bootstrap.fltkg` - Minimal grammar for bootstrapping
- `fegen.fltkg` - Full grammar definition
- `fltk.fltkg` - Extended grammar with advanced features

## Requirements

- Python 3.7+
- Dependencies: `astor`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `hatch run lint:all` to check style
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/rnortman/fltk/issues)
