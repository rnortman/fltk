# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. It uses a custom grammar format (.fltkg files) to generate parsers that produce Concrete Syntax Trees (CST).

## Development Commands

### Testing
```bash
# Run all tests
hatch run test

# Run tests with coverage
hatch run cov

# Run tests with specific args
hatch run test path/to/specific/test.py
```

### Linting and Formatting
```bash
# Check style and types
hatch run lint:all

# Format code
hatch run lint:fmt

# Check types only
hatch run lint:typing

# Check style only
hatch run lint:style
```

### Build System
The project uses both Hatch (Python) and Bazel build systems:
- Hatch: Primary Python package management and testing
- Bazel: Alternative build system with MODULE.bazel configuration intended for adding fltk as a dependency in other projects using Bazel.

## Architecture

### Core Components

1. **Grammar System** (`fltk/fegen/`):
   - `.fltkg` files define grammars using custom syntax
   - `bootstrap.fltkg`: Bootstrap grammar for parsing grammar files
   - `fegen.fltkg`: Full grammar definition for the system
   - `gsm.py`: Grammar Semantic Model - core data structures for representing grammars

2. **Parser Generation**:
   - `bootstrap_parser.py`: Generated parser for bootstrap grammar
   - `fltk_parser.py`: Generated parser for full grammar
   - `gsm2parser.py`: Converts GSM to parser code
   - `gsm2tree.py`: Converts GSM to CST node classes

3. **Intermediate Representation** (`fltk/iir/`):
   - `model.py`: Type system and data model definitions
   - `typemodel.py`: Type modeling infrastructure
   - `py/`: Python-specific compilation and code generation

4. **Runtime Support** (`fltk/fegen/pyrt/`):
   - `memo.py`: Packrat parsing memoization
   - `errors.py`: Error tracking and reporting
   - `terminalsrc.py`: Terminal/token source handling

### Key Files

- `bootstrap2gsm.py`: Converts bootstrap CST to GSM
- `bootstrap_cst.py`: Bootstrap CST node definitions
- `fltk2gsm.py`: Converts full grammar CST to GSM
- `genparser.py`: Main parser generation entry point
- `pygen.py`: Python code generation utilities

### Grammar Format

The `.fltkg` grammar format supports:
- Rule definitions with `:=`
- Alternatives with `|`
- Item separators: `.` (no whitespace), `,` (whitespace allowed), `:` (whitespace required)
- Quantifiers: `?` (optional), `+` (one or more), `*` (zero or more)
- Dispositions: `%` (suppress), `$` (include), `!` (inline)
- Labels for capturing specific parts: `label:term`
- Literals, regexes, and sub-expressions

### CST Design

- Each grammar rule generates a corresponding node class
- Nodes maintain references only to children (no parent/sibling refs)
- Spans track source text positions
- Type-safe child access methods based on labels
- Suppressed elements may create gaps in spans

## Configuration

- `pyproject.toml`: Hatch configuration, dependencies, and tool settings
- `pytest.ini`: Test configuration with debug logging enabled
- `requirements_lock_3_10.txt`: Locked dependencies for Python 3.10
- Black line length: 120 characters
- Target Python version: 3.8+