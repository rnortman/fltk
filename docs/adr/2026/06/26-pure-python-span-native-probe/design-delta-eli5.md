# ELI5: The Delta Design — Isolating the Python Pipeline from Rust Types

This document explains a design amendment (the "delta") in plain terms. It assumes you know
general software engineering but nothing about FLTK, its internals, or the Python type-checking
concepts at play. Everything you need is introduced as we go.

## What this is about

### The system in a nutshell

FLTK is a toolkit for building parsers and compilers. You write a grammar (a description of a
language's syntax), and FLTK generates parser code and a set of typed data classes (called a
Concrete Syntax Tree, or CST) that represent a parsed document as a tree of nodes.

A "span" is a small object that records where in the source text a parsed element came from — its
start position, end position, and a reference to the original text. Every CST node carries a span.

FLTK has two backends:

1. **Pure-Python backend.** The parser, CST nodes, and spans are all ordinary Python code. The span
   type lives in a module called `terminalsrc` (`terminalsrc.Span`).
2. **Rust backend.** A compiled native extension (`fltk._native`) provides its own parser, CST
   nodes, and span type (`fltk._native.Span`). It is faster but requires a Rust toolchain to build.

The user chooses which backend they want by importing the corresponding parser. Whichever backend
they pick, all of their downstream code — the code that reads and walks the CST — should work
identically without caring which backend produced the tree. This "swap-ability" is the central
contract: a set of Python protocols (interfaces) that both backends satisfy, so consumer code can
be written once and work with either.

### The base design (already partially implemented)

Before this delta, a "base design" was written and partially implemented. It fixed a runtime bug:
the pure-Python parser was accidentally constructing Rust spans (when the Rust extension happened
to be installed) because of a process-wide "probe" in a module called `span.py`. That module's
`try/except` block would silently swap in Rust types whenever the native extension was importable.
The base design fixed this by making the Python parser always construct `terminalsrc.Span` objects
directly, bypassing the probe. It also removed a defunct "hybrid" code path (a Python parser
feeding Rust CST nodes) that had no use case.

However, the base design left the **type annotation surface** — the types that Python's static
type checker (pyright) sees when analyzing the code — pointing at the old probe module (`span.py`).
It planned to bridge a resulting type mismatch with a `typing.cast` (a directive that tells the
type checker "trust me, this value is really type X" even though the checker cannot prove it). That
cast turned out to be the wrong fix, and the delta design replaces it with a proper solution.

### The bug the delta fixes

Python projects commonly use a tool called pyright for static type analysis. Pyright reads type
annotations and checks that values flow correctly between them. FLTK runs pyright as part of its
standard check suite (`make check`).

The `span.py` selector module uses a `try/except` pattern to conditionally import the Rust span:

```python
try:
    from fltk._native import Span        # Rust span
except Exception:
    from fltk.fegen.pyrt.terminalsrc import Span   # Python span
```

When pyright analyzes this, it always takes the `try` branch as authoritative — it does not
simulate import failures. The project ships a type stub file (`.pyi`) for `fltk._native` — a file
that tells pyright what types the Rust extension provides, even without building the extension.
Because that stub is committed to the repository and always present, pyright always resolves
`span.Span` to `fltk._native.Span` — the Rust type.

This was confirmed by direct pyright probes against the real modules. The reality is in fact worse
than the initial framing: the entire pure-Python pipeline is type-checked as if it produces Rust
spans. This directly refutes the base design's claim that pyright sees "the union of both
backends" — it sees only the Rust type.

Two concrete problems result:

1. **The pure-Python parser constructs `terminalsrc.Span` but its return annotations say
   `span.Span` (which pyright reads as `fltk._native.Span`).** The parser's internal return type,
   `ApplyResult`, is "invariant" in its type parameter — meaning the type checker demands an exact
   match, not a subtype or supertype. Constructing a Python span but annotating it as a Rust span
   is a type error. This was the blocker that prevented the base design's code-regeneration step
   from passing type checks.

2. **If someone removes the `.pyi` stub file**, pyright does not fall back to the `except` branch.
   Instead, `span.Span` resolves to `Unknown`. The type error from problem 1 disappears (because
   `Unknown` is compatible with everything), but the analysis is now different. The same code
   produces different pyright diagnostics depending on whether an unrelated stub file exists. This
   instability is exactly the property the user says must not hold.

The base design's planned fix was a `typing.cast`. The user rejected this as masking the problem
rather than fixing it. The delta replaces it with honest types.

## The relevant parts of the system

To follow the fix, a few more pieces of context are needed.

**The type registry** is an internal mechanism in FLTK's code generators (`context.py`). When the
generators need to emit a type annotation for "span," they look up a registry entry keyed by the
short name `Span`. That single registry entry drives annotations in the parser, the CST node
classes, the protocol definitions, and the unparser — all from one shared entry. Before this delta,
the entry pointed at `span.py`, so every generated annotation resolved through the selector — and
therefore to the Rust type under pyright.

**Invariance** is a type-system concept that matters here. Some generic types are "invariant" in
their parameters, meaning if you declare a container of type X, you can only put exact-type-X
values in it — not subtypes, not supertypes, not "similar" types. `ApplyResult` (the parser's
internal result wrapper) is invariant. Mutable dataclass fields are also effectively invariant.
This is the strictest form of type-parameter matching and is what makes the Rust-vs-Python
mismatch a hard type error rather than a soft one.

**`SpanProtocol`** is a Python protocol (structural interface) that describes the span API: start
position, end position, merge, intersect, and so on. Both `terminalsrc.Span` and
`fltk._native.Span` are supposed to satisfy it, so code written against `SpanProtocol` works with
either backend. However, before this delta, `SpanProtocol` had a latent conformance bug: its
`merge` and `intersect` methods accepted `other: SpanProtocol` (any protocol-conforming span),
while each concrete span's methods accept only their own type. In type-theory terms, method
parameters are contravariant — a method that accepts a narrower type than the protocol requires
makes the concrete class fail to satisfy the protocol. This was invisible because no code actually
assigned a concrete span value into a `SpanProtocol`-typed slot under pyright's scrutiny.

**Generated files vs. generator files.** FLTK's code generators (`gsm2parser.py`, `gsm2tree.py`,
`gsm2unparser.py`, `gsm2tree_rs.py`) produce generated output files (parsers, CST classes,
protocols, Rust `.pyi` stubs). The delta changes the generators so the output they produce has
honest, stable type annotations. The generated output files are public API for downstream consumers
outside this repository.

## What the delta changes and why

The root cause is that one registry entry for `Span` is being asked to serve two fundamentally
different roles:

- **Concept A: the concrete Python parser's span.** The parser constructs `terminalsrc.Span` and
  returns it in an invariant `ApplyResult`. The annotation must exactly match the constructed type.
- **Concept B: the backend-agnostic CST span contract.** CST nodes, protocols, and Rust `.pyi`
  stubs expose a span field that both backends' spans must satisfy. This slot must name a single
  type that both backends conform to, without naming either backend specifically.

One shared registry entry cannot serve both: invariance demands an exact concrete type for the
parser, while cross-backend agnosticism demands a shared abstract type for the CST surface. The
delta separates them.

### Making SpanProtocol actually usable as an agnostic type

For `SpanProtocol` to work as the CST's span type, concrete span values must be assignable to
`SpanProtocol`-typed slots. Before this delta, they were not, due to the contravariance issue
described above. Two changes fix this:

1. **`merge` and `intersect` use `Self` instead of `SpanProtocol`.** The signature becomes
   `def merge(self, other: Self) -> Self`, meaning "merge only with another span of the same
   concrete type." This is semantically more honest — at runtime, a `terminalsrc.Span` already
   raises when asked to merge with a span from a different source, so "merge only with your own
   backend's span" is the true contract. The `Self` type comes from `typing_extensions` (the
   project targets Python 3.10, where `typing.Self` is not yet available). With this change,
   `terminalsrc.Span` values become statically assignable to `SpanProtocol`-typed variables,
   parameters, and dataclass fields — confirmed by pyright probes.

2. **A `kind` property is added to the protocol.** Both concrete span types already expose this
   property (a discriminant that identifies the object as a span vs. a node). Adding it to the
   protocol is needed for a pattern-matching dispatch mechanism in the generated CST code: consumer
   code uses `match child.kind` to distinguish span children from node children, and the `kind`
   property must be declared in the protocol for pyright to verify the match arms.

These are compatible refinements: both backends already satisfy them at runtime.

The protocol's body imports only from `terminalsrc` — it does not name `fltk._native`. A separate
`AnySpan` symbol in the same module does probe for native, but it is a standalone utility not
referenced by the pipeline (more on this in the open question below).

### Splitting the type registry

The shared `Span` registry entry is split into two distinct registrations:

- **The registry's `Span` entry is repointed** from `span.Span` to
  `span_protocol.SpanProtocol`. This single change flows through to every registry-driven
  annotation automatically: CST node span-typed children, protocol span-typed children, and the
  unparser's span parameter. Since `SpanProtocol` is defined in pure Python (depending only on
  `terminalsrc`, never on `fltk._native`), pyright resolves it identically regardless of whether
  the Rust stub exists.

- **A new parser-local type is registered** in the parser generator, pointing at
  `terminalsrc.Span`. This gives the parser an honest annotation for its invariant `ApplyResult`
  returns: it constructs `terminalsrc.Span` and annotates it as `terminalsrc.Span` — exact match,
  no cast needed.

- **The `SourceText` entry also moves** from `span.py` to `terminalsrc`. This is a critical
  implementation detail: `SourceText` is registered in two places — the central context module
  and the parser generator — and both must move together. Repointing only the central context
  while leaving the parser generator's re-registration at `span.py` would cause a hard crash:
  the two registrations would disagree for the same key, and the code raises a conflict error.
  The `SourceText` type is used only by the parser for its `_source_text` field, so making it
  honest removes another selector reference with no conformance impact.

### Parser annotations become honest

The parser's terminal-consume helpers, which match literal strings and regex patterns, now return
`ApplyResult[int, terminalsrc.Span]` instead of `ApplyResult[int, span.Span]`. Because
`ApplyResult` is invariant and the constructed value is a `terminalsrc.Span`, this is the only
annotation that satisfies pyright without a cast.

The `typing.cast` from the base design is eliminated entirely. It is unnecessary: the parser's
constructed `terminalsrc.Span` values flow into CST node fields now annotated as `SpanProtocol`,
and after the `SpanProtocol` root-fix, `terminalsrc.Span` is assignable to `SpanProtocol`. Both
the parser's internal invariant returns and the parser-to-CST boundary are honest — confirmed by
pyright probes with zero errors.

The parser no longer imports `span.py` at all — not at runtime (already fixed by the base design)
and not under `TYPE_CHECKING` (the base design still had this; the delta removes it, and nothing
replaces it). The parser references only `terminalsrc` for span and source-text types, plus the
CST node types it populates. The `from __future__ import annotations` directive may remain
(harmless; avoids churn).

### CST and protocol annotations move to SpanProtocol

The generated CST node classes and their protocol counterparts previously annotated their `span`
field with an explicit union of the Python and Rust span types
(`terminalsrc.Span | fltk._native.Span`), and their span-typed children with `span.Span` (via the
registry). Both of these named Rust types and resolved through the selector.

After the delta, all of these become `SpanProtocol`. The concrete CST dataclass keeps its default
value of `terminalsrc.UnknownSpan` (a Python span representing "no span information"), which is
assignable to `SpanProtocol` after the root-fix. The imports change: `import fltk._native` and
`import fltk.fegen.pyrt.span` are dropped; `import fltk.fegen.pyrt.span_protocol` replaces them.

A small marker class used for pattern-matching dispatch (`_protocol_span_class`) is unchanged: it
provides the value matched against in `case` statements. The subject expression `child.kind` now
typechecks because the child union's span member is `SpanProtocol`, which carries `kind` after the
root-fix.

Runtime mutator validation logic (the `isinstance` checks that guard CST mutation methods) is also
unchanged — it uses runtime type checks against concrete types and is independent of the static
annotation.

### Rust .pyi stub follows the same pattern

The Rust backend's type stub (`.pyi` file) annotates its CST nodes' span positions. These must
match the protocol so a consumer can swap backends. Before the delta, the stub used the explicit
union annotation. After, it uses `SpanProtocol` — the same agnostic type the Python CST uses. The
runtime span objects in a Rust CST remain `fltk._native.Span`; the declared type is the shared
contract. This mirrors exactly how the Python CST annotates its `terminalsrc.Span` runtime objects
as `SpanProtocol`.

The stub's imports add `fltk.fegen.pyrt.span_protocol` and drop `fltk._native` and `span` if
nothing else in the stub references them. No Rust CST class is renamed — only the span type name
in annotations changes.

### Unparser annotations follow suit

The generated unparser's span parameter annotation was driven by the same registry entry, so it
becomes `SpanProtocol` automatically via the registry repoint. Its `TYPE_CHECKING` import switches
from `span` to `span_protocol`. The runtime dual-backend span guard (`is_span`, from the base
design) is unchanged — it is a runtime mechanism that handles both backends and is unaffected by
annotation changes.

## Why this particular split — and why alternatives do not work

The split is not a design preference; it is forced by the type system. This was verified with
pyright probes, not asserted.

**"Use `terminalsrc.Span` everywhere" does not work for the cross-backend surface.** The Rust
`.pyi` stub would have to annotate its native span children as `terminalsrc.Span`, which is a lie
about the Rust backend. The project's guidelines explicitly state that the Rust backend must still
get Rust types. A shared invariant slot needs a shared name both backends satisfy, and a
Python-specific concrete type cannot be that name.

**"Use `SpanProtocol` everywhere" does not work for the parser.** The parser's `ApplyResult` is
invariant. Constructing `terminalsrc.Span` but annotating it `ApplyResult[int, SpanProtocol]` is
the exact same invariance failure as the Rust case — `terminalsrc.Span` is not the same type as
`SpanProtocol` — and would require a `typing.cast`, the very workaround the user rejected.

**The base design's `typing.cast` is rejected.** It is unnecessary once the parser uses honest
annotations (`terminalsrc.Span`) and once `SpanProtocol` is assignable from concrete spans (so the
parser-to-CST boundary needs no cast either). The cast masked the mismatch rather than fixing it,
which is precisely what the user said not to do.

So each surface gets the only type its constraints allow: the invariant single-backend parser
return gets the concrete `terminalsrc.Span`; the invariant cross-backend CST slot gets
`SpanProtocol`. The shared agnostic name across protocols, both concrete backends' CST, and the
Rust stub is `SpanProtocol` — a single pure-Python name that names neither backend and resolves
identically with or without the native stub.

## What stays the same from the base design

Several pieces of the base design were already implemented and remain untouched:

- **Runtime construction:** The Python parser always constructs `terminalsrc.Span` objects
  (base design section 2.1, committed). Only parser *annotations* change.
- **Warning removal:** The noisy fallback warning in `span.py` was already deleted. The
  `try/except` selector logic remains (for standalone use), but falls back silently.
- **Hybrid path removal:** The ability to use a Python parser with a Rust CST was already deleted
  per the user's directive (base design section 2.3, committed). Not reintroduced.
- **Dual-backend `is_span` guard:** The unparser's runtime span recognizer (base design section
  2.6(a), committed) stands unchanged.

After this delta, nothing in the pipeline imports `span.py` — not at runtime (fixed earlier) and
not under `TYPE_CHECKING` (removed by this delta). That is the complete isolation the user demands.

## What could go wrong and how it is handled

**Pyright stability across stub presence/absence.** The central goal. Generated pipeline modules
(parser, CST, protocol, unparser) name neither `fltk._native` nor the `span.py` selector after
this delta. `SpanProtocol` resolves through `span_protocol.py`, which depends only on
`terminalsrc`. Pyright's inferred types and diagnostics on the generated pipeline are therefore
identical whether the Rust type stub is present or absent. A new regression test verifies this
directly by running pyright on a representative generated triad (parser + CST + protocol) with the
stub present and with the stub absent, and asserting identical results.

**Native `fltk._native.Span` is not statically assignable to `SpanProtocol`.** The Rust span's
`line_col()` method returns the Rust backend's `LineColPos` type, which is nominally distinct from
`terminalsrc.LineColPos`. This means pyright would reject assigning a native span value into a
`SpanProtocol`-typed variable. This does not block the design: the only place a span value is
statically assigned into a `SpanProtocol` slot within the type-checked scope (`fltk/`, `*.py`) is
the Python parser using `terminalsrc.Span` — which does conform after the root-fix. The Rust
`.pyi` only declares `span: SpanProtocol` without assigning values. Cross-backend tests live
outside pyright's configured scope and read spans rather than assign native spans into
`SpanProtocol` slots. The gap is tracked as a TODO for future work (unifying `LineColPos` across
backends) — it is a contained, pre-existing technical issue, not a blocker.

**Shape-2 dispatch (pattern matching on span kind).** The CST consumer code uses
`match child.kind` to distinguish span children from node children. With the span member of the
child union now typed as `SpanProtocol` (which carries the `kind` property after the root-fix),
this dispatch continues to typecheck. Existing cross-backend dispatch tests remain valid.

**`span.py` and `AnySpan` still probe for native — but outside the pipeline.** No generated
parser, CST, protocol, or unparser module imports `span.py` at runtime or under `TYPE_CHECKING`
after this delta. No generated module imports `span_protocol` at runtime either (only under
`TYPE_CHECKING`), and the error formatter (`error_formatter.py`) runtime-imports `SpanProtocol`
but generated parsers do not import the error formatter. The pipeline never triggers a native
probe, even indirectly. `span.py` and `AnySpan` remain as tested standalone utilities.

**`SourceText` annotation honesty.** The parser's `_source_text` field becomes
`terminalsrc.SourceText`, matching its `terminalsrc.SourceText(...)` construction. No selector
reference remains.

**Regeneration scope widens.** The base design's regeneration step only affected parser files.
This delta also changes generated CST (`*_cst.py`) and protocol (`*_cst_protocol.py`) files, since
their span annotations and imports change. The standard `make gencode` followed by `make fix` must
produce exactly these diffs, and `make check` must pass — both style/formatting (ruff) and type
checking (pyright) — with no cast.

**Public API annotation change is deliberate.** The project's guidelines (CLAUDE.md) forbid
incidental annotation churn on generated public symbols. This delta changes the span type name in
annotations from `span.Span` / the explicit union to `SpanProtocol`, and that change is
deliberate, justified, and user-directed ("change all type annotations to the span protocol").
No generated class, method, accessor, label, or enum is renamed. Consumers who read span values
and call span methods are unaffected — `SpanProtocol` carries the full span API. The only consumers
who would need to update are those who pinned a concrete span type name (`fltk._native.Span` or
`fltk.fegen.pyrt.span.Span`) on a value sourced from a CST accessor — and pinning
`fltk._native.Span` on a pure-Python CST was the bug being fixed. The agnostic replacement is
`SpanProtocol`, which the requirements mandate for swap-ability. The parser's internal annotation
change (`span.Span` to `terminalsrc.Span`) is parser-internal: no consumer annotates
`ApplyResult[int, span]`; the public entry points return CST node types.

**Pre-existing test suites that pin the old surface.** Several existing tests assert the old
annotation surface (e.g., asserting that a `.pyi` imports `fltk._native` or that the span field
is the explicit union). These tests will break because the delta deliberately changes that surface.
The delta requires them to be retargeted to assert the new surface (e.g., the `.pyi` imports
`span_protocol` and annotates `span: SpanProtocol`) or retired with an explicit stated rationale,
rather than silently left to fail. The test plan in the delta enumerates each affected suite and
its disposition.

## What is still open

There is one genuine open question that requires the user's judgment.

### Should the now-pipeline-unused native probes be purged entirely?

After this delta, nothing in the generated Python pipeline (parser, CST, protocol, unparser)
imports `span.py` (the backend selector) or triggers `span_protocol.AnySpan`'s native-presence
check. Both remain as standalone, tested public utilities. A consumer can still
`import fltk.fegen.pyrt.span` to discover which backend is active, and `AnySpan` provides a
union type of all known span implementations.

The pipeline-scoped reading of the user's requirement ("the Python pipeline never imports Rust,
even indirectly") is satisfied without touching these utilities. They are outside the pipeline.

However, the requirement has a second, broader clause: "Pyright should produce the same results
when analyzing Python code whether the Rust backend is importable or not." Read repo-wide, that
broader clause is **not** met under the "keep both" default. Here is why:

- `span.py`'s `try/except` block causes `span.Span` to resolve to `fltk._native.Span` (with the
  stub present) or `Unknown` (with the stub absent). Pyright's analysis of `span.py` and anything
  that imports it changes depending on the stub.
- `span_protocol.py`'s `AnySpan` definition similarly flips between
  `terminalsrc.Span | fltk._native.Span` and just `terminalsrc.Span` depending on stub presence.
- Both files live inside `fltk/`, which is within pyright's configured analysis scope
  (`make check`).

The generated pipeline is stub-stable either way (it does not import these modules). Only these
two standalone utilities are stub-sensitive.

**What hangs on the answer:** If the user wants the narrow, pipeline-scoped interpretation of the
stability requirement, the delta is complete as-is — the pipeline is fully isolated and
stub-stable. If the user wants the broad, repo-wide interpretation (no stub-sensitive pyright
result anywhere in `fltk/`), then the selector concept itself must be retired: delete `span.py`
as a public module and drop `AnySpan`'s native arm. That would be a separate public-API removal
requiring its own decision, since downstream consumers may import `span.py` today.

The delta defaults to keeping both utilities intact and surfaces the tradeoff for the user to
decide rather than resolving it in either direction.
