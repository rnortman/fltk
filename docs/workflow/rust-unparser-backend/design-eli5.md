# Rust Unparser Backend -- ELI5

## What this is about

FLTK is a toolkit for building parsers and compilers. You give it a grammar file describing a language, and it generates two things for you: a **parser** (which reads source text and produces a structured tree representation called a Concrete Syntax Tree, or CST) and an **unparser** (which takes a CST and turns it back into nicely formatted source text). Both of these are code generators -- they produce code that your application then compiles and uses directly.

Until recently, both generators produced Python code only. The parser generator then gained a second backend that emits Rust code instead of Python. This Rust parser backend has two layers: a pure-Rust core with zero Python dependencies (usable in any Rust application), and an optional PyO3 wrapper that lets Python code call into the Rust parser. The PyO3 wrapper is gated behind a Cargo feature flag, so it is only compiled when needed.

The unparser generator is still Python-only. This design adds a Rust backend for the unparser, following the same two-layer pattern the parser established.

### Why the unparser is not trivial

One might imagine the unparser simply walks the tree and concatenates text. It does not. The Python unparser is a three-stage formatting pipeline:

1. **Unparse.** A generated class walks the CST and builds a tree of formatting instructions called a `Doc` tree. This tree is not text -- it is a structured representation of the desired output, including things like "group these items together," "indent this block," "put a soft line break here that becomes a real line break only if the line is too wide." The tree is built through an immutable accumulator that threads state through the walk.

2. **Resolve spacing.** A resolution pass rewrites abstract spacing-control nodes (like "put spacing after this item" or "use this separator between items") into concrete spacing decisions. This handles things like merging adjacent spacing requests, preserving whitespace from the original source (trivia), and collapsing redundant blank lines.

3. **Render.** A Wadler-Lindig pretty-printer turns the resolved `Doc` tree into a final string. It makes width-aware decisions: if a group of items fits on one line, keep it flat; otherwise break it across lines with proper indentation. This is configurable with an indent width and a maximum line width.

None of this formatting machinery exists in Rust today. The Rust unparser backend must reproduce all three stages.

### Why this matters for external consumers

FLTK's primary purpose is to be used by other applications that live outside this repository. Those applications generate parsers and unparsers for their own languages, then write code against the generated classes and methods. The generated class name `Unparser` and the method names `unparse_{rule}` are public API. Renaming them or forcing wholesale changes to call sites would break downstream consumers. This constraint shapes several decisions below.

## The relevant parts of the system

### How the Rust CST works

The Rust CST generator (already existing) produces a Rust struct for each grammar rule. Each struct holds a list of children, where each child is a pair: an optional label (an enum variant identifying what role the child plays) and a child value. The child value is itself an enum with one variant per possible child type -- a `Span` variant for terminal tokens (literal text or regex matches) and one variant per referenced grammar rule (wrapping a shared pointer to that rule's struct).

This enum-based child type is important for the unparser. In Python, the unparser uses `isinstance` checks and a helper function `is_span` to figure out what kind of child it is looking at. In Rust, a `match` on the child enum does the same job -- and does it exhaustively at compile time.

### How Rust spans differ from Python spans

In the Python backend, spans (which track where a piece of text came from in the source) do not carry the source text themselves. The unparser must receive the entire source string as a constructor parameter (`terminals`) and slice into it to recover text. In the Rust backend, each span carries a reference-counted pointer to its source text and exposes a `text()` method that returns the text directly (or `None` if the span has no source). This means the Rust unparser never needs a `terminals` parameter -- it gets text straight from the span.

### How formatting configuration works

The unparser's behavior is partly controlled by a `FormatterConfig`, which specifies things like spacing defaults, grouping and indentation anchors, and how to handle trivia (comments, whitespace). This configuration is consumed entirely at generation time -- the generator reads the config and bakes the decisions into the emitted code. The generated unparser has no runtime configuration for formatting rules; the only runtime inputs are the CST to unparse and (for the renderer) the line width and indent size.

## What we are going to do and why

### Three new pieces

The design adds three things, each mirroring something the parser backend already has:

1. **A new runtime crate** (`crates/fltk-unparser-core`) -- the shared, grammar-independent Rust library that provides the `Doc` type, the accumulator, the spacing resolver, and the renderer.

2. **A new code generator** (`fltk/unparse/gsm2unparser_rs.py`) -- a Python class that, given a grammar, emits a `.rs` file containing a Rust unparser with an optional PyO3 wrapper.

3. **CLI, build system, and test wiring** -- a new command-line subcommand, Makefile targets, and a test fixture with cross-backend parity tests.

### Why a separate generator instead of modifying the existing one

The existing Python unparser generator works by building an intermediate representation (IIR) that gets compiled into Python AST nodes. The Rust backend does not retarget this IIR -- instead, it is a separate generator that directly emits Rust source code as a string, just as the Rust parser generator does. This keeps the Python backend and its public API at zero risk of accidental breakage and keeps the two generators side-by-side for easy comparison, exactly matching how the parser's two generators (`gsm2parser.py` and `gsm2parser_rs.py`) coexist today.

### The runtime crate

The crate `fltk-unparser-core` is a direct, faithful port of the Python formatting pipeline into Rust. It has no PyO3 dependency (matching `fltk-parser-core`'s convention) and no dependency on the CST crate either -- the runtime operates on `Doc` trees, not on CST nodes. Terminal text is extracted in the generated code (which does depend on the CST crate) and passed into the runtime as `Doc::text(String)`.

The crate has five modules:

- **`doc.rs`** -- the `Doc` enum, with roughly 15 variants matching the Python hierarchy: `Text`, `Comment`, `Line`, `Nbsp`, `SoftLine`, `HardLine`, `Group`, `Nest`, `Concat`, `Join`, `Nil`, `AfterSpec`, `BeforeSpec`, `SeparatorSpec`. Children are wrapped in `Rc` (reference-counted pointers) so that the accumulator's clone-heavy usage and the resolver's rewriting share structure cheaply, mirroring how Python's frozen dataclasses share references. Helper constructors handle things like flattening nested `Concat` nodes and eliding `Nil`, matching the Python helpers.

- **`accumulator.rs`** -- `DocAccumulator`, an immutable persistent data structure built as an `Rc`-linked chain of nodes, with push/pop operations for entering and leaving `Group`, `Nest`, and `Join` contexts. Cloning is cheap (just bumping reference counts). Mismatched push/pop (which can only happen due to generator bugs) produces the same diagnostic messages as the Python version.

- **`resolve.rs`** -- `resolve_spacing_specs`, the pass that expands joins, extracts boundary specs, resolves patterns, collapses hardline sequences, and merges spacing. This is a literal port of the Python `resolve_specs.py`, with Python's deque-based working set becoming a `VecDeque`.

- **`render.rs`** -- the Wadler-Lindig renderer with configurable indent width and max line width (defaulting to 4 and 80, matching Python). The Python renderer is already iterative (queue-based, not recursive), and the port preserves that.

- **`result.rs`** -- `UnparseResult`, a simple struct pairing a `DocAccumulator` with a child-position index (the `new_pos` that tells the caller where to continue in the children list).

The crate is added to the Cargo workspace alongside the existing `fltk-cst-core` and `fltk-parser-core` crates.

### The code generator

The new generator, `RustUnparserGenerator`, takes a grammar and an optional `FormatterConfig` and produces a single `.rs` file. Internally it creates a `RustCstGenerator` (the existing CST generator) to reuse its naming helpers -- functions that compute names like `ExprChild`, `ExprLabel`, `PyExpr` from a grammar rule. The `generate()` method is idempotent (calling it twice returns the same string), matching the parser generator's convention.

The generated code follows the same structural pattern as the Python unparser, but expressed in Rust. For each grammar rule, the generator emits:

- A public method `unparse_{rule}` that creates a fresh accumulator, applies any rule-level formatting anchors (begin a group, begin indentation, etc.), dispatches to the rule's alternatives, and applies closing anchors on success.

- Private helper methods for alternatives, items, and quantified loops, each taking the CST node, a position index, and an accumulator, and returning `Option<UnparseResult>`. The accumulator is threaded by value (cheap to clone). A `None` return from any sub-step causes the current alternative to fail and the next to be tried, mirroring the Python control flow.

The key translation from Python to Rust at each step:

- **Type dispatch.** Python uses `isinstance` and `is_span` to distinguish children. Rust uses a `match` on the child enum -- `Span(span)` for terminals, `SomeRule(shared)` for rule references. A mismatched variant returns `None`, letting the next alternative try.

- **Text extraction.** Python calls `extract_span_text(span, self.terminals)`. Rust calls `span.text()`, which returns `Option<String>`. If a span has no source text (which only happens with hand-built CSTs, not parser output), the rule returns `None` rather than silently producing empty text.

- **Formatting config.** The generator reads `FormatterConfig` at generation time and emits Rust `Doc` constructor expressions for the configured spacing. A helper function `_doc_to_rust_expr` converts a `Doc` value into the Rust expression that constructs it -- covering `Nil`, `Nbsp`, `Line`, `SoftLine`, `HardLine`, `Text`, and `Concat`. It deliberately rejects `Group`, `Nest`, and `Join` with the same error as the Python backend's equivalent helper. This matters because a format config could theoretically specify a join separator that is itself a `Group` -- the Python backend already rejects this at generation time, and the Rust backend must reject it identically rather than silently succeeding, which would make the two backends diverge.

- **Item-level anchor operations.** Beyond rule-level group/nest/join, the format config can specify anchors at item granularity -- "start a group at this label, end it at that label." These become accumulator push/pop calls emitted inline in the alternative's code, exactly paralleling what the Python generator does.

The generated struct is a unit struct (`pub struct Unparser;`) with a no-argument constructor. There is nothing to configure at construction time: the formatting rules are baked into the generated code, and the Rust CST carries its own source text.

### The PyO3 wrapper layer

The generated file includes a `#[cfg(feature = "python")]` section with a `PyUnparser` class. This is where the design makes a deliberate, documented divergence from the Python backend's API shape.

In the Python backend, `unparse_{rule}(node)` returns an intermediate `UnparseResult` (the `Doc` tree inside an accumulator). The caller is responsible for feeding that through `resolve_spacing_specs` and then `Renderer.render` to get a string. This chaining lives in driver code (`plumbing.py`), not in the generated class.

In the Rust PyO3 wrapper, each `unparse_{rule}` method runs the full pipeline -- unparse, resolve, render -- and returns the final formatted string directly (or `None` if unparsing fails). It accepts `max_width` and `indent_width` as optional parameters (defaulting to 80 and 4).

The reason for this divergence: exposing the intermediate `Doc` tree and `UnparseResult` to Python would require wrapping the entire `Doc` type hierarchy in PyO3 bindings, which is a significant amount of work that the requirements do not ask for. Returning the rendered string keeps the PyO3 surface simple. Cross-backend correctness is verified by comparing rendered strings (the parity tests assert byte-equal output), not by comparing intermediate representations.

For pure-Rust consumers, the stages remain separate: `unparse_{rule}(node)` returns the `Doc`-producing `UnparseResult`, and the consumer chains resolution and rendering themselves. The string convenience lives only in the PyO3 layer, matching how in Python the chaining lives in the driver, not the generated class.

The PyO3 wrapper accepts only the Rust CST handles (`Py{ClassName}` types), not pure-Python CST objects. PyO3's argument extraction enforces this automatically -- passing a Python-backend CST object simply fails type checking. This enforces the rule that the Rust unparser must be paired with the Rust parser.

The Python-visible class name is `Unparser` and the methods are `unparse_{rule}`, preserving the public symbol names from the Python backend. The two known differences from the Python surface are both called out explicitly: (1) the constructor takes no arguments (Python's takes `terminals`), and (2) the methods return a formatted string instead of an intermediate `UnparseResult`.

For downstream consumers migrating from the Python unparser to the Rust one, the change at each call site is bounded and mechanical: the three-step `unp.unparse_x(node)` / `resolve_spacing_specs(...)` / `render_doc(...)` chain becomes a single `unp.unparse_x(node, max_width, indent_width)` call.

### CLI, Makefile, and LibSpec wiring

A new CLI subcommand `gen-rust-unparser` is added to `genparser.py`, accepting a grammar file, an output file, an optional `--cst-mod-path` (defaulting to `super::cst`), and an optional `--format-config` pointing to a `.fltkfmt` file. This mirrors the existing `gen-rust-parser` subcommand.

The `Makefile` gets a corresponding target, and the fixture's unparser regeneration is wired into the `gencode` master target. The new crate is added to the clippy and `cargo test` lanes.

The lib.rs generator (`gsm2lib_rs.py`) is extended: `LibSpec.standard()` gains a `with_unparser` parameter. When true, an `unparser` submodule is added alongside the existing `cst` and `parser` submodules. The registration function name stays `register_classes`, consistent with the existing convention.

### Test fixture

Rather than creating a new fixture crate, the design extends the existing `tests/rust_parser_fixture/` crate. This fixture already has a grammar that exercises a broad surface -- literals, regex terminals, labels, all quantifier types, separator variants, sub-expressions, union labels, suppress/include dispositions, and left recursion. Adding an unparser to it gives good coverage without duplicating the grammar.

A small `.fltkfmt` format config is added for the fixture grammar, exercising not just default spacing but also before/after anchors, rule-level group/nest/join, and at least one item-level anchor range operation (like "group from label X to label Y"). This ensures the non-trivial formatting pipeline paths are tested, not just the simplest cases.

## What could go wrong and how it is handled

### Deep trees and stack overflow

The `Doc` tree's depth is proportional to the CST's depth, which can be very large for deeply nested input. In Python, excessively deep recursion hits a catchable `RecursionError`. In Rust, a stack overflow is an uncatchable abort -- the process dies. The Rust CST already dealt with this by implementing iterative (non-recursive) `Drop`, `PartialEq`, and `Debug`.

The design handles this in two parts: (a) `Doc` gets an iterative `Drop` implementation (a worklist-draining loop instead of recursive destructor calls), because `Drop` fires on every happy path and a stack overflow there would be a hard crash. (b) The `resolve_spacing_specs` function's internal recursion is left matching Python's recursion depth for now, since the renderer is already iterative and the resolver mirrors Python's behavior exactly. Whether to harden the resolver against adversarial depth is open question 1.

### Sourceless spans

A `Span` can lack source text -- this happens with hand-built CSTs or sentinel values like `Span::unknown()`. When the Rust unparser encounters such a span for a terminal that should have text, the enclosing rule returns `None` (unparse failure) rather than silently producing empty text. CSTs produced by the Rust parser always carry source text, so this is a safety net for edge cases, not something that fires in normal use.

### Required suppressed regex or identifier terms

Some grammar terms are "suppressed" -- they appear in the grammar but not in the CST. If a suppressed term is a literal (like a keyword), the unparser can reconstruct it from the literal text in the grammar. But if a suppressed term is a regex or an identifier reference, the unparser cannot know what text to emit -- that information was discarded when the term was suppressed. In this case, the generator raises an error at generation time (not at runtime), with the same error messages as the Python backend.

### Union labels and alternative fallthrough

When a label can refer to multiple child types, the unparser matches on the specific child enum variant it expects. If the variant does not match, the alternative returns `None` and the next alternative is tried. This is the same control flow as the Python backend's `isinstance` failure path.

### Lock safety

The Rust CST uses `Arc<RwLock<T>>` for shared ownership of nodes. The unparser only read-locks children during traversal and performs no Python callbacks mid-walk (it builds a pure-Rust `Doc` tree). Holding nested read guards down the tree is safe and deadlock-free. No node is mutated during unparsing.

### Generation drift

The committed fixture `.rs` files must match what the generator produces. The existing `make gencode` + `git diff` workflow catches any hand-patches or stale generated code.

## Test plan

Four levels of testing:

1. **Runtime crate unit tests** (pure Rust, no Python): exercise `Doc` construction, accumulator operations (including push/pop mismatches), spacing resolution (spec merging, join expansion, hardline collapsing, trivia precedence), and renderer behavior (flat-vs-break decisions, indentation, blank lines, width-driven breaking). Test cases are seeded from the existing Python test suites.

2. **Generator tests** (Python): verify that the generated Rust source contains expected structures, that generation raises on invalid configurations (like required-suppressed-regex), and that `generate()` is idempotent.

3. **Cross-backend parity tests** (Python, with `pytest.importorskip`): a shared corpus of `(rule, text)` pairs is parsed with both backends (Python and Rust), unparsed with both, rendered to strings with matching configuration, and asserted byte-equal. The corpus includes both default formatting and the fixture's `.fltkfmt` config, plus bounded nesting depths.

4. **Native Rust fixture tests** (pure Rust, no Python): build a CST via the native Rust API, run the unparser, and assert the rendered string -- proving the core links and runs with no Python runtime.

## What is still open

### Open question 1: How far to go on deep-tree stack safety

The `Doc` tree can be as deep as the CST, which can be arbitrarily deep for adversarial input. The design hardens `Doc::drop` (making it iterative so the destructor does not overflow the stack), but defers hardening the `resolve_spacing_specs` function's internal recursion. The rationale: the renderer is already iterative, and the resolver mirrors Python's recursion exactly, so initial behavior is at parity.

The question is whether this parity-first approach is acceptable for the initial milestone (with a tracked TODO for hardening the resolver later), or whether adversarial-depth safety must be fully addressed now. The argument for deferring: this is an initial port, and matching Python's behavior is the stated goal; Python itself would hit a `RecursionError` at the same depth. The argument for doing it now: the Rust CST already set a precedent of iterative implementations, and a stack overflow in Rust is an uncatchable process abort, worse than Python's catchable exception.

### Open question 2: Should the PyO3 layer also expose the intermediate Doc

The design settles on a string-returning API for the PyO3 wrapper -- each `unparse_{rule}` method runs the full pipeline and returns the formatted string. This decision is made and is not in question.

The open question is whether to *additionally* expose the intermediate `Doc` tree (or per-stage handles) to Python. This would be purely additive -- the string-returning method stays regardless. The use case: a Python caller might want to unparse once and then render at multiple line widths without re-walking the CST, or might want to inspect the formatting structure for debugging. The cost: wrapping the `Doc` type hierarchy in PyO3 bindings, which is nontrivial given the roughly 15 variants and recursive structure. The answer to this question does not affect the core design -- it only determines whether the PyO3 surface gets additional methods later.

### Open question 3: Should the generator emit a .pyi type stub

The Rust CST backend emits a `.pyi` file so that Python type checkers can see the types of the generated CST classes. The unparser has no analogous protocol requirement, but a `.pyi` stub would give downstream Python consumers type-checked access to the `Unparser` class and its methods. The alternative is leaving the Rust unparser's Python surface untyped for now. This is a convenience/polish question with no impact on functionality or correctness.
