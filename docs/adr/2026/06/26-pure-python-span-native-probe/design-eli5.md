# ELI5: Two backends only -- Python parser to Python CST, Rust parser to Rust CST

This document explains the approved design at `./design.md` for a reader who has never seen this codebase before. It adds no decisions, constraints, or recommendations beyond what the design contains.

## What this is about

FLTK is a toolkit for building parsers. You give it a grammar -- a formal description of a language's syntax -- and it generates parser code that can read text in that language and produce a tree structure called a Concrete Syntax Tree (CST). Each node in the CST carries a "span" that records where in the original source text that node came from: a start position and an end position. When you match a keyword or identifier, the parser wraps the matched text range in a span object and attaches it to the CST node.

FLTK has two completely separate implementations of all of this:

- A **pure-Python** implementation. The parser is generated Python code. The CST nodes are Python dataclasses. The span and source-text objects come from a module called `terminalsrc` -- ordinary Python classes.
- A **Rust** implementation. The parser, CST nodes, and spans are compiled Rust code exposed to Python through a native extension module called `fltk._native`. This is faster but requires the extension to be compiled and installed.

The intended contract is that a downstream application -- code living outside the FLTK repository -- chooses which implementation to use by importing the corresponding parser. Import the Python parser, get an all-Python stack. Import the Rust parser, get an all-Rust stack. The two backends satisfy the same protocols (shared interfaces), so code that *consumes* the CST (walks the tree, inspects nodes, reads spans) can work with either backend without changes.

FLTK's generated CST node classes, parsers, protocols, and their type annotations are public API consumed by real downstream applications that live outside this repository. Any change that forces those consumers to update their type annotations or call sites is a breaking change. This constraint is central to every decision in this design.

That is the intended architecture. It is not what actually happens today.

## The bug

There is a module called `span.py` that acts as a process-wide backend selector. The first time anything imports it, it runs a small probe: a try/except block that attempts to import the Rust extension. If the extension is installed, `span.py` re-exports the Rust `Span` and `SourceText` types. If the extension is absent, it falls back to the pure-Python types from `terminalsrc` and prints a warning.

Every generated pure-Python parser imports `span.py` at the top of its file, at module scope, because the parser's runtime code -- the calls that actually construct span objects during parsing -- references names from that module. This means importing any pure-Python parser triggers the probe.

The consequence: in any Python process where the Rust extension happens to be installed, a "pure-Python" parser silently produces Rust-backed span objects in its CST nodes. The span backend is not determined by which parser you chose; it is determined by whether a compiled extension happens to be present. This is the core bug. As the project owner stated: "It is incorrect for the pure-Python parsers to use Rust-backed span."

The warning is a secondary symptom. When the Rust extension is absent, the probe's fallback path emits a noisy `UserWarning`. There is nothing wrong with a pure-Python parser running without the Rust extension -- that is the expected, correct scenario -- so the warning is spurious.

Both the silent type substitution and the warning come from the same mechanism.

## The dual role of span.py

Fixing the bug is complicated by the fact that `span.py` serves two distinct purposes at once:

**Runtime span construction.** Generated parsers call `fltk.fegen.pyrt.span.Span.with_source(...)` and `fltk.fegen.pyrt.span.SourceText(...)` at runtime to build span and source-text objects during parsing. This is where the bug lives: the probe picks the wrong concrete types.

**Backend-agnostic type name.** Throughout the generated CST files, protocol definitions, and type stubs, annotations reference `fltk.fegen.pyrt.span.Span` as a backend-agnostic type that covers both the Python and Rust implementations. Type checkers resolve it to a union of both backends, which is how both flavors of CST satisfy the same protocol. Downstream consumers annotate their code with these names. This is load-bearing public API.

The design must fix the runtime construction problem without disturbing the annotation surface. Changing the annotations would force every downstream consumer to update their type declarations -- exactly the kind of churn the project forbids.

## The hybrid path and why it is being removed

There is a third configuration in the current codebase that does not belong: a "hybrid" mode where a Python parser is paired with a Rust CST module. The library's `plumbing.py` has parameters (`rust_cst_module`, `rust_fegen_cst_module`) that let a caller generate a Python parser but have it populate Rust CST nodes instead of Python ones.

This hybrid was scaffolding from the Rust backend's development. The project owner's directive is unambiguous: "There is no use case for a python parser producing rust CST. We should rip that out."

Removing the hybrid path simplifies the fix considerably. The hybrid was the only reason a Python parser would ever need to construct Rust spans -- the Rust CST nodes contain a function called `extract_span` that accepts only native Rust spans and rejects pure-Python ones with a `TypeError`. With no hybrid path, a Python parser never feeds spans to Rust CST nodes, so there is no reason for it to ever construct anything other than `terminalsrc` spans. There is no selector to build, no mode flag to propagate. The Python parser just always uses `terminalsrc`, unconditionally.

After removal, exactly two valid configurations remain, chosen by which parser the consumer imports:

1. **Pure-Python parser produces pure-Python spans and pure-Python CST.** No Rust extension, no probe.
2. **Rust parser produces Rust spans and Rust CST.** This is a compiled PyO3 extension that parses natively and constructs `fltk._native.Span` internally. It never touches `span.py` or the Python codegen pipeline at all.

## The design

The fix has four parts: retarget runtime construction, stop importing `span.py` at runtime, remove the warning, and delete the hybrid plumbing. Each is explained below with the reasoning behind its approach.

### The Python parser always constructs terminalsrc types

There are two places in the parser code generator (`gsm2parser.py`) that emit runtime construction calls -- the code that actually builds span and source-text objects during parsing:

**The span-construction site.** Every time the parser matches a terminal (a token like a keyword or number), it calls `Span.with_source(start, end, source_text)` to record where the token came from. Today, the code generator looks up `Span` in a shared type registry, gets back the module path `fltk.fegen.pyrt.span`, and emits `fltk.fegen.pyrt.span.Span.with_source(...)`. The fix replaces this with a hardcoded reference to `fltk.fegen.pyrt.terminalsrc.Span.with_source(...)`, bypassing the registry for this construction call.

**The source-text initializer.** When the parser starts, it creates a `SourceText` object holding the entire input text, which all spans then reference. This one is trickier. Today it is built using a higher-level code-generation construct (an IIR `Construct` node) that resolves its class name through the type registry. The registry entry points at `span`, so a `Construct` would compile to `fltk.fegen.pyrt.span.SourceText(...)` -- reintroducing the runtime `span` import. We cannot change the registry entry because it drives annotations too, and changing it would churn the public API surface. Instead, the fix replaces the `Construct` node with a lower-level, registry-independent call expression that spells out `fltk.fegen.pyrt.terminalsrc.SourceText(...)` directly. This mirrors the pattern used for the span-construction site.

The type registry entries themselves are left untouched. They still say `Span` and `SourceText` live in `fltk.fegen.pyrt.span`. Every annotation derived from them continues to reference `span.py`, preserving the backend-agnostic public surface. Construction and annotation are now decoupled: construction goes directly to `terminalsrc`; annotations go through the registry to `span`.

### Generated parsers stop importing span.py at runtime

Today, the generated parser files have "eager" annotations: Python evaluates type annotations as expressions at import time. Because some annotations reference `fltk.fegen.pyrt.span.Span`, the parser must import `span.py` at the top of the file, which triggers the probe.

The fix adds `from __future__ import annotations` to generated parser files, making all annotations "lazy" -- they become unevaluated strings, never resolved at runtime. The `span.py` import is moved inside a `TYPE_CHECKING` block, so it is visible only to type checkers like pyright, never executed at runtime. This is exactly the pattern that generated CST files already use.

After this change, at runtime a generated Python parser imports only `terminalsrc` (and a few other pure-Python modules like `memo` and `errors`). It constructs `terminalsrc.Span` and `terminalsrc.SourceText` deterministically. It never touches `span.py` at runtime, so the probe never fires and the warning never appears.

### The warning is removed from span.py

The `warnings.warn(...)` call and the `import warnings` line are deleted from `span.py`. The try/except re-export structure is kept: `span.py` remains the public, tested backend selector (a test asserts that when the native extension is built, `span.Span` is the native type). The except branch now falls back silently, matching the pattern already used in `span_protocol.py`, a sibling module that does the same probe without a warning.

### The hybrid plumbing is deleted

The Python-parser-with-Rust-CST option is removed from `plumbing.py`:

- The `rust_cst_module` parameter is removed from `generate_parser`. The function always generates and uses Python CST classes.
- The `rust_fegen_cst_module` parameter is removed from `parse_grammar` and `parse_grammar_file`. These functions always use the committed Python parser and Python CST.
- Several support functions and classes that existed only for the hybrid path are deleted: the Rust-CST-class loader (`_load_rust_cst_classes`), the `RustBackendUnavailableError` exception, associated caches (`_fegen_rust_parser_cache`, `_fegen_grammar_cache`), the `_load_fegen_grammar` helper, and the now-unused `importlib` import. Some of these (like `_fegen_grammar_cache`, a module-level global) would not be caught by linting tools if left behind, so they must be deleted explicitly.

An important subtlety: the in-memory parser that `generate_parser` builds by exec'ing generated code also needs the lazy-annotations treatment. Today its eager annotations happen to work only because importing `fltk_parser` (done elsewhere in `plumbing.py`) loads `span.py` as a side effect. Once the earlier changes remove that side effect, eager annotation evaluation would raise an `AttributeError`. Adding `from __future__ import annotations` to the exec'd code makes its annotations lazy strings, removing the dependency. Only the `terminalsrc` construction names need to resolve at runtime, and `terminalsrc` is already bound in the exec environment.

These functions (`generate_parser`, `parse_grammar`) are FLTK library entry points, not generated public symbols that downstream consumers annotate against. Removing a keyword-only parameter that selected a path with no use case does not touch the generated CST or parser surface. This is a deliberate, user-directed API removal.

## What does NOT change

The design is explicit about what is frozen:

- The type registry entries for `Span` and `SourceText` stay pointed at `fltk.fegen.pyrt.span`. Every annotation derived from them is unchanged.
- Generated CST node files (`*_cst.py`): the span field union annotation, span-typed child annotations, accessor return types, mutator logic, `NodeKind`/`Label` equality -- all unchanged.
- Generated protocol files (`*_cst_protocol.py`) and Rust `.pyi` stubs: unchanged.
- `span.py` retains its backend-selector semantics (only the warning is removed).
- No generated public symbol is renamed. No downstream type annotation is forced to change. Consumer code remains agnostic to which backend produced the CST.

After the change, committed parser files are regenerated (`make gencode`, then `make fix` to normalize formatting). The regenerated parsers gain `from __future__ import annotations`, move the `span` import under `TYPE_CHECKING`, and change their construction calls from `fltk.fegen.pyrt.span.*` to `fltk.fegen.pyrt.terminalsrc.*`.

## What could go wrong and how it is handled

**The core bug scenario: pure-Python parser in a process where the Rust extension is installed.** After this change, construction targets `terminalsrc` unconditionally. The produced span is `terminalsrc.Span`. No probe runs. A new regression test covers this directly: parse text with a committed Python parser, assert that `type(node.span) is terminalsrc.Span`.

**Rust extension genuinely absent in a pure-Python install.** The parser imports only `terminalsrc` at runtime. Nothing imports `span.py`, so there is no warning and no `ImportError`. The `_native`-referencing annotations under `TYPE_CHECKING` are lazy strings that are never evaluated at runtime.

**Cross-backend span comparison in parity tests.** Some tests compare a CST produced by the Python parser against one produced by the Rust parser. After this change, the Python CST has `terminalsrc.Span` objects and the Rust CST has `fltk._native.Span` objects. These two types are not equal via `==` even for the same text range. The existing parity helpers already handle this: they compare spans by `.start` and `.end` values, not by object equality. No regression. This is verified in the codebase, not assumed.

**In-memory exec'd parser annotations.** When `plumbing.py` generates a parser at runtime by exec'ing generated code, the exec'd code contains `span.Span` annotations. Today these resolve only because a side effect loads `span.py` into the process. The design removes that side effect, so the exec'd code gets `from __future__ import annotations` prepended, making its annotations lazy strings. Only the `terminalsrc` construction names need to resolve at runtime, and `terminalsrc` is already bound in the exec environment.

**Removing hybrid parameters breaks in-tree callers.** Several tests pass `rust_cst_module` or `rust_fegen_cst_module`. These tests are removed or retargeted (see below) as part of this change. No out-of-tree generated-symbol surface is affected.

**Linting and type-checking on regenerated parsers.** The new `from __future__ import annotations` and `TYPE_CHECKING` import pattern must pass ruff and pyright. This is the exact pattern generated CST files already use and pass, so the risk is low. The regeneration drift check enforces it.

## Tests removed, retargeted, and added

Tests that enforce the presence of the hybrid path are removed because the hybrid path itself is removed. But where a test covers a still-valid property -- particularly cross-backend dispatch agnosticism (proving that consumer code produces identical results regardless of backend) -- the test is retargeted rather than deleted.

The most important retargeting: `TestCrossBackendDualShapeDispatch` currently obtains its Rust CST by running the hybrid path (Python parser producing Rust CST nodes). It is the only test that verifies a consumer's pattern-matching and tree-walking code works identically on both backends -- exactly the swap-ability the requirements mandate. Rather than deleting it and losing that coverage, the design retargets it to obtain its Rust CST from the genuine Rust parser (the all-Rust configuration 2 path). The assertions stay the same; only the source of the Rust CST changes from the deleted hybrid to the real Rust parser.

A separate test (`test_fltk2gsm_behavioral_equivalence`) that also used the hybrid path is simply deleted: its property (that converting a CST to a grammar model produces the same result regardless of backend) is already covered by the kept `TestRustParserSelfHosting` test, which does the same comparison using the real Rust parser.

New tests are added to cover the fix directly: a regression test asserting that a Python parser produces `terminalsrc.Span` even when `_native` is importable; a source-inspection test asserting the committed parser imports `span` only under `TYPE_CHECKING` and constructs via `terminalsrc`; and a test asserting no `UserWarning` is emitted when using a pure-Python parser.

## What is still open

The design records no open questions requiring further judgment. One alternative was considered and explicitly rejected:

**Making span annotations backend-specific instead of backend-agnostic.** One could make the Python CST's annotations say `terminalsrc.Span` and the Rust CST's say `fltk._native.Span`, instead of both using the agnostic `fltk.fegen.pyrt.span.Span`. This was rejected because it would change the public annotation surface of every generated CST and protocol file, forcing downstream consumers to update their type declarations. The agnostic name is what lets consumer code work with either backend without changes. The runtime objects are already correct after the construction-site retargeting, and consumers remain backend-agnostic through the shared protocol. Making annotations "honest per backend" would deliver no runtime benefit while imposing a migration cost on every downstream consumer.
