# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-07-24

This release adds two major capabilities on top of a year of hardening: an optional
**Rust backend** for generated parsers and CSTs, and a full **language-server
toolchain** for FLTK grammars. The alpha unparser/formatter from 0.2.0 also matured.
The Python backend remains the default and its public API is unchanged.

### Rust backend (alpha)

FLTK can now generate a Rust implementation of the CST and parser alongside the Python
one. The goal is a near-drop-in replacement: a downstream project can switch its
generated parser and CST to the Rust backend and, at most, update its import
statements — type annotations and call sites are meant to keep working unchanged.

- CST and parser code generation in Rust, with a backend selector so a grammar can
  target the Python or the Rust implementation.
- A Rust implementation of the unparser/formatter, plus a standalone pure-Rust
  `fltkfmt` binary that formats `.fltkg` files without a Python runtime.
- Generated Rust nodes own their children as `Shared<T>` (an `Arc<RwLock<T>>` newtype),
  so cloning a node is a shallow reference clone. Child identity now matches the Python
  backend: reading the same child twice yields the same object, and mutations are
  visible through every reference and across the language boundary.
- Type-stub (`.pyi`) emission for the generated extension, and hardening of the
  cross-cdylib ABI so a compiled parser can be loaded safely from a consumer module.

Treat the Rust backend as early alpha.

### Language Server Protocol tooling

- `fltk-lsp`, a pygls-based language server that drives editor features directly from
  an FLTK grammar.
- A `.fltklsp` spec language and classification engine for semantic highlighting, with
  a companion `fltk-highlight` CLI.
- Definition, reference, and namespace navigation for grammars; prefix-CST exposure so
  incomplete input still highlights gracefully; a resolver plugin API; and a VS Code
  integration.
- FLTK now dogfoods these servers on its own grammars.

### Unparser and formatter improvements

- New `preserve_blanks: N` directive to preserve and normalize runs of blank lines.
- Comment handling fixes: inline comments stay on the line they annotate, comments
  between rules attach to the following rule, and spurious blank lines no longer appear
  between commented alternatives.
- New documentation: `docs/format-specs.md` (format-spec reference) and `docs/usage.md`
  (CLI usage).

### Robustness and security

- Generated parsers enforce a configurable recursion-depth limit, preventing
  stack-exhaustion denial-of-service on pathological input.
- A forged-ABI code path that could segfault the Rust backend was closed, and error
  messages emitted by generated parsers are now properly escaped.
- Grammar generation catches more latent bugs up front: non-portable regexes, empty
  `_`-named rules, and identifier collisions are now rejected at generation time.

### Build, CI, and dependencies

- Supply-chain and toolchain hardening: `cargo-deny` gating, pinned CI actions managed
  by Dependabot, a pinned Rust toolchain mirrored across the cargo and Bazel lanes, and
  lockfile-drift gates.
- Dependencies were refreshed across the board (Python, Rust, and CI actions), which
  included moving to a newer ruff and clearing the resulting lint/format findings.

## [0.2.0]

The main feature here is alpha-level support for generating unparsers and source
code formatters from FLTK grammars. Various small bugs and enhancements are also
included; see detailed chages in the changelog.

### Utilities for dynamically generating and running parsers/unparsers

There is a new `fltk.plumbing` module that makes it easy to dynamically generate
and run parsers/unparsers, and also `unparse_cli` which lets you do this from
the command line.

### Detect repeated potentially-nil items

If you have a rule like:

foo := ("a"? ,)*;

This can match the empty string an arbitrary number of times, which previously
would lead to the parser hanging in an infinite loop. We fix this bug by
detecting potentially-nil repeated items at parser generation time, making it
easier to detect this grammar bug.

### Unparser and Formatter support (alpha)

A huge new feature: We can generate unparsers and formatters from FLTK grammars.
This means that given a CST, you can generate source code that parses to that
CST, meaning you can round-trip source and reformat it, as well as write
refactoring tools that parse a file, modify the CST, and then write out the
modified source without relying on fragile regex-based string matching and
replacement.

Unparsing will not always regenerate exactly the same source text, but it should
regenerate something semantically equivalent (i.e., something that produces the
same CST result). Formatting is based on Wadler-Lindig Pretty-Printing
Combinators with some extensions, and is controlled by a new fltkfmt DSL.

Unparsing and formatting support should be considered early alpha. It may be
buggy and we may make breaking changes to the fltkfmt DSL or how it works.
Unparsing is substantially more complex, it turns out, than parsing.

### Allow leading whitespace/trivia

Rule alternatives can now start with a separator spec to indicate leading
trivia. In particular this is very useful for allowing the grammar as a whole to
begin with trivia.

### Move python files out of repo root

All python source was moved into the fltk package. This is a breaking change for
anything directly referring to those files, though anything using the bazel
rules will not need to change since the rules were updated as well.

## [0.1.1] - 2025-07-03

Fix a regression caused by renaming the trivia rule to use all caps. This turns
out to be a bit of a problem with linters on the generated parsers, so we now
use `_trivia` instead of `_TRIVIA`.

## [0.1.0] - 2025-07-02

The major change in 0.1.0 is the addition of trivia support, i.e. being able to
have comment syntax in your language. ("Trivia" is just compiler-nerd jargon for
"comments and whitespace".) This release also includes a lot of general code
cleanups and modernization.

### Dev environment modernization and build integration
- Migrate dev environment from hatch to uv and mypy to PyRight
- Fix all PyRight errors and update formatting rules
- Update Bazel rules for uv and dual-parser generation
- Small code cleanups; remove dead code
- Overhaul genparser.py CLI with Typer interface

### Add trivia support (comments and whitespace)
- Implement trivia as normal grammar productions under special name _TRIVIA
- Force trivia-within-trivia to be plain whitespace
- Generate CST node clases for trivia
- Generate two different parsers per grammar: One which produces trivia CST nodes and a faster one that doesn't
- Add comment support to FLTK grammar itself

### Refactoring and cleanup
- Add a README
- Fix linting and typing issues
- Remove global singleton type registry
- Add regression test for recursive rules inlining bug
- Add regression test for WS_REQUIRED walrus operator precedence bug
- Regression test for Fix error reporting at EOF
- Add regression test for empty N-ary nodes bug
- Add regression test for top-level rule recursion bug
- Add regression test for line/col error reporting bug
- Fix trailing character parsing bug

### Bug Fixes (June 2024)
- Fix bug with inlining recursive rules

### Bug Fixes (Spring 2024)
- Fix bug in WS_REQUIRED
- Fix error reporting at end of file
- Fix bug with detecting empty N-ary nodes
- Fix bug with recursion on top-level rule
- Fix bug in line/col error reporting
- Fix a bug with multi-path left recursion

## [0.0.1] - 2023-11-06

### Initial Build System Setup
- Set up pyproject, linters, reformatting
- Set up Bazel workspace and rule
- Small fixes to Bazel module definition
- Fix unnecessary type cast in gencode
- Small mypy fixes, and add py.typed
- Add missing srcs/deps

### Core Features Implemented
- Custom grammar notation (.fltkg format) for defining parsers
- Self-hosting parser generator - the grammar parser is itself generated from a grammar
- Packrat parsing with memoization for O(N) performance
- Type-safe Concrete Syntax Tree (CST) generation
- Source span tracking for all parsed nodes
- Python code generation for parsers
- Support for left-recursive grammars
- Development tooling with ruff, pyright, and pytest

[Unreleased]: https://github.com/rnortman/fltk/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rnortman/fltk/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rnortman/fltk/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/rnortman/fltk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rnortman/fltk/releases/tag/v0.1.0
[0.0.1]: https://github.com/rnortman/fltk/releases/tag/v0.0.1