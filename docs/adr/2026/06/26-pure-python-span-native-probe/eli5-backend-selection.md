# The Native Warning and Backend Selection -- What the Explorations Found

## What this is about

FLTK is a toolkit for building parsers.  You describe a language's grammar, and FLTK generates a parser (Python code) that can read text in that language and produce a tree of nodes representing the parsed structure.  That tree is called a Concrete Syntax Tree (CST).

When a parser reads your text, it needs to track *where* each piece of text came from -- character positions, line numbers, that sort of thing.  FLTK represents that positional information with objects called **Spans**.  A Span says "this node came from characters 5 through 12 of the input."  To share the underlying source text efficiently across many Spans, there is also a **SourceText** object that holds the full input string.

FLTK has two implementations of Span and SourceText:

- A **pure-Python** implementation, in a module called `terminalsrc.py`.  It is a straightforward Python dataclass.
- A **native (Rust)** implementation, compiled via PyO3 into a shared library called `fltk._native`.  It does the same job but faster, because Rust code handles memory more compactly and the spans share a single UTF-8 buffer instead of each carrying a Python string reference.

The native implementation is optional.  Building it requires a Rust toolchain (`rustup`, `cargo`, `maturin`).  If you install FLTK without Rust, you get the pure-Python spans, which are slower and use more memory.

These explorations examine a **warning message** that fires whenever you use FLTK without the native extension installed.  The warning says "fltk._native could not be loaded; falling back to pure-Python Span backend."  The explorations cover the warning and the options for removing or changing it.

## The relevant parts of the system

### The backend selector: `span.py`

There is a small module, `fltk/fegen/pyrt/span.py`, whose only job is to decide which Span implementation to use.  It works like this:

1. First, it imports the pure-Python versions of `Span`, `SourceText`, and `UnknownSpan` from `terminalsrc.py`.
2. Then it tries to import the same names from `fltk._native` (the Rust extension).
3. If the Rust import succeeds, the native types silently overwrite the pure-Python ones.  From that point on, anyone who asks `span.py` for `Span` gets the Rust version.
4. If the Rust import fails, the pure-Python types stay in place -- but the module also emits a `warnings.warn()` call, which is the warning this exploration is about.

This try/except block runs exactly once per Python process, the first time `span.py` is imported.  After that, Python's module cache (`sys.modules`) serves the already-loaded result.

### How generated parsers end up importing `span.py`

When FLTK generates a parser from a grammar, the generated Python code contains lines like `fltk.fegen.pyrt.span.SourceText(text=..., filename=...)` and `fltk.fegen.pyrt.span.Span.with_source(start, end, ...)`.  These are actual function calls that run when the parser parses text -- they are not just type annotations.  So the generated parser must `import fltk.fegen.pyrt.span` at the top of the file, at module scope, unconditionally.

This import path is baked in at code-generation time.  The FLTK code generator maintains a "type registry" that maps abstract types like "Span" to concrete module paths.  Both `Span` and `SourceText` are registered with the module path `fltk.fegen.pyrt.span`.  The code generator then emits that path verbatim into every generated parser.  There is no flag, parameter, or configuration to make it emit `fltk.fegen.pyrt.terminalsrc` instead.

The result: every generated parser, when imported, triggers `span.py`'s native probe.

### What does NOT trigger the probe

Generated CST node files (the classes that represent each node in the tree) handle this differently.  They only reference `span.py` and `fltk._native` inside `if typing.TYPE_CHECKING:` blocks, which means those imports only run when a type checker like pyright analyzes the code -- never at runtime.  So importing a CST file never triggers the native probe or the warning.

There is also a second native probe in a related file, `span_protocol.py`.  That file checks for `fltk._native` to build a union type (`AnySpan`) that can accept both Python and Rust spans.  But it does so **silently** -- no `warnings.warn`.  This silent-fallback pattern already exists in the codebase.

### `terminalsrc.py` is self-contained

The pure-Python implementation (`terminalsrc.py`) imports nothing from `_native` or from `span.py`.  It is completely independent.  Importing it never triggers any native probe or warning.

## What the explorations found

### The warning is purely informational

The warning does not gate any logic.  It does not change what code runs afterward.  The try/except fallback works identically whether or not the `warnings.warn` call is present.  Removing it changes nothing about FLTK's behavior.

### No tests assert on the warning

A thorough search of all test files found no test that checks for this specific warning text, no use of `pytest.warns` or `recwarn` related to it, and no `filterwarnings` configuration that references it.  Removing the warning will not break any test.

### What the probe does

The *probe* -- the try/except that attempts to import from `fltk._native` -- is load-bearing.  When the native extension is available, the probe causes the Python-generated parser to produce Rust-backed Span objects instead of pure-Python ones.  Rust spans are cheaper to allocate and share a single UTF-8 buffer rather than each span holding a reference to a Python string.

Without the probe, even a system with the Rust extension installed would produce pure-Python spans from its Python-generated parsers.

### Why a pure-Python parser probes the native backend at all

The probe in `span.py` is unconditional and process-wide.  It does not know or care whether the caller is a pure-Python parser, a Rust-backed parser, or something else entirely.  There is no concept of a "backend selection flag" at this level.

The explorations identify three separate, orthogonal choices in FLTK's architecture:

1. **Parser logic**: Is the parser itself Python code or compiled Rust code?  This is a build-time decision.  The `plumbing.generate_parser` function always generates a Python parser; there is no runtime switch.

2. **CST node classes**: Are the tree node classes Python dataclasses or Rust-backed PyO3 objects?  This is controlled by a `rust_cst_module` parameter.  But regardless of this choice, the parser logic is always Python.

3. **Span type**: Are spans pure-Python or native Rust?  This is controlled solely by `span.py`'s probe -- and it fires for all parsers equally, without regard to choices (1) or (2).

The result is that even in a "fully pure-Python" scenario -- Python parser logic, Python CST classes, no Rust toolchain installed -- the generated parser still imports `span.py`, which still tries to load the Rust extension, which fails, which emits the warning.  The parser then produces pure-Python spans.

## The three candidate fixes

The explorations identify three possible responses.

### Option 1: Remove the warning, keep the probe

Delete the `warnings.warn(...)` call and the `import warnings` statement from `span.py`.  Leave the try/except block and its fallback logic completely intact.

**What it does:** The user no longer sees the warning when using FLTK without the Rust extension.  The fallback to pure-Python spans continues to work exactly as before.  The optimization (using native spans when available) also continues to work.

**What it does not change:** The generated parser still probes for `fltk._native` on every import, even in a pure-Python installation where that probe will never succeed; it is a single failed import, caught and discarded.

**Scope:** One file, a few lines.

### Option 2: Make the probe conditional

Instead of always probing for `fltk._native`, make the probe contingent on some signal that the native backend is wanted or expected.  For example, an environment variable, a configuration flag, or a parameter passed through the code generator.

**What it does:** Pure-Python parsers would never attempt to import `fltk._native`.

**Obstacles:** `span.py` is a module.  It runs its top-level code once, on first import.  At that point, it has no context about *who* is importing it or *why*.  There is no "current parser" or "current backend mode" to consult.  The module system does not provide the kind of caller-awareness that would be needed.  Some mechanism would have to be invented to communicate this information -- an environment variable, a prior import that sets a flag, or a fundamentally different import pattern.

**What the explorations note:** This approach is architecturally absent today.  There is no existing flag, parameter, or configuration point that distinguishes "we want native spans" from "we want pure-Python spans."  Building one would require new design work.

### Option 3: Restructure so pure-Python parsers never import `span.py`

Change the code generator's type registry so that pure-Python parsers import `Span` and `SourceText` directly from `terminalsrc.py` instead of from `span.py`.  Reserve `span.py` (and its native probe) for contexts that actually want the native-if-available behavior.

**What it does:** Pure-Python parsers would have no connection to the native backend at all -- no probe, no fallback, no warning.

**Obstacles:** The type registry in `context.py` and `gsm2parser.py` hardcodes the module path `("fltk", "fegen", "pyrt", "span")` for both `Span` and `SourceText`.  There is no parameterization -- a single `create_default_context` function always registers `span` as the source.  Making this configurable would require changes to the type registry, the code generator, and potentially the way parsers are instantiated.

**What the explorations note:** `terminalsrc.py` has no native imports and is self-contained; the plumbing to route the code generator there does not exist.

## What hangs on these choices

For end users (people who install FLTK without a Rust toolchain and generate parsers), the only visible difference between the three options is whether they see a warning.

The explorations lay out the facts -- what would need to change, what exists today, what is missing -- but do not prescribe an answer.  The explorations do not claim Option 2 or Option 3 is necessary.
