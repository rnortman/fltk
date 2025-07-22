# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. It uses a custom grammar format (.fltkg files) to generate parsers that produce Concrete Syntax Trees (CST).

## Development Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run coverage run -m pytest && uv run coverage report

# Run tests with specific args
uv run pytest path/to/specific/test.py
```

### Linting and Formatting
```bash
# Check style and types
uv run ruff check . && uv run pyright

# Format code
uv run ruff format .

# Check types only
uv run pyright

# Check style only
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Build System
The project uses both setuptools (Python) and Bazel build systems:
- uv: Primary Python package management and testing
- Bazel: Alternative build system with MODULE.bazel configuration intended for adding fltk as a dependency in other projects using Bazel.

## Development Protocols

Almost all changes should follow Test-Driven Design (TDD): First write a set of tests that fail but will pass when your task is done, and then complete the task.

When you identify a bug, first implement the test that demonstrates the bug (if there isn't one already) before fixing the bug.

TDD is all that's needed for straightforward changes.
For more complex changes, follow the Design-Test-Code (DTC) process, which is just TDD but with a design stage first, where you will plan out your implementation approach and API surfaces.
For even more complex changes, follow Explore-Design-Test-Code (EDTC), where you first read necessary context and clarify requirements and approach interactively with the user.

You may find when you are designing, testing, or coding, that you don't understand something.
That indicates that you should stop and start an Explore-Design-Test-Code (EDTC) process.

Remember that any of these phases can be interactive with the user, especially Explore and Design phases.
The user is a smart human and likely knows more than you do about this codebase and the requirements.

## Architecture

### Core Components

1. **Grammar System** (`fltk/fegen/`):
   - `.fltkg` files define grammars using custom syntax
   - `fegen.fltkg`: Full grammar definition for the system
   - `gsm.py`: Grammar Semantic Model - core data structures for representing grammars

2. **Parser Generation**:
   - `fltk_parser.py`: Generated parser for full grammar
   - `gsm2parser.py`: Converts GSM to parser code
   - `gsm2tree.py`: Converts GSM to CST node classes

3. **Intermediate Representation** (`fltk/iir/`):
   - `model.py`: Type system and data model definitions
   - `typemodel.py`: Type modeling infrastructure
   - `py/`: Python-specific compilation and code generation

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

- `pyproject.toml`: uv configuration, dependencies, and tool settings
- `pytest.ini`: Test configuration with debug logging enabled
- Black line length: 120 characters
- Target Python version: 3.10+

## Working tips

Always read the entire file when reading a source file.
Trying to read only a few lines at a time usually leads to misunderstandings.
Don't search for specific lines and try to read only those; just read the whole file.
