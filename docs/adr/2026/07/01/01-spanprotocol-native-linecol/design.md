# Design: `spanprotocol-native-linecol` — structural `LineColPosProtocol`

Requirements: `request.md` (same directory). Exploration: `exploration.md` (same directory).

## Root cause / context

`SpanProtocol.line_col` / `line_col_or_raise` (`fltk/fegen/pyrt/span_protocol.py:97,105`) are
annotated to return `terminalsrc.LineColPos`, a nominal class. The native backend's
`fltk._native.Span.line_col` returns `fltk._native.LineColPos` — a genuinely separate
PyO3-compiled class (`crates/fltk-cst-core/src/span.rs`, declared in
`fltk/_native/__init__.pyi:14-28`). Pyright therefore rejects assigning a native span into a
`SpanProtocol` slot (exploration §3 reproduces the exact diagnostic: the only incompatible
member named is `line_col`, a return-type covariance failure on the nominal `LineColPos`
mismatch).

`SpanProtocol` is the documented cross-backend annotation type for downstream code
(`span_protocol.py:18-23`: "Backend-agnostic code should annotate with `SpanProtocol`"). Per
CLAUDE.md, the Rust backend's promise is near-drop-in replacement; an out-of-tree consumer
following the documented pattern currently type-fails the moment a native span reaches a
`SpanProtocol`-annotated slot. The gap is contained in-tree only because exactly one in-scope
site statically assigns a span value into a `SpanProtocol` slot, and it deliberately uses the
Python backend (`fltk/fegen/pyrt/test_span_protocol_assignability.py:33`; exploration §4).

The two `LineColPos` classes cannot be unified nominally: making the native backend return the
Python dataclass (or vice versa) would create a cross-backend import dependency, breaking the
pure-Python/native isolation established by the `2026/06/26-pure-python-span-native-probe`
delta series (exploration §6). `TODO.md`'s older "one shared nominal type" phrasing predates
that verification; `request.md` supersedes it with the structural shape.

**Load-bearing constraint (request.md):** `span_protocol.py` must keep naming zero
`fltk._native` symbols. The generated pipeline's pyright stub-stability holds structurally
only because `SpanProtocol`'s definition depends solely on `terminalsrc` (delta D5.1), and no
existing test covers that transitive property — the "names no native" tests
(`test_cst_protocol.py`, `test_genparser.py`, `test_gsm2tree_rs.py`, `test_is_span_guard.py`)
scan generated-file text only and structurally cannot catch a regression in
`span_protocol.py` itself (exploration §5). The fix must add a guard for this.

## Proposed approach

### Verified feasibility

A pyright probe (run during design with the repo's locked pyright, 1.1.402, same config `make
check` uses) confirmed the full shape with **0 errors**: a structural `LineColPosProtocol` with
read-only properties (`line: int`, `col: int`, `line_span: SpanProtocol`), plus `SpanProtocol`'s
`line_col`/`line_col_or_raise` retyped to return it, makes **both** `terminalsrc.Span` and
`fltk._native.Span` statically assignable to `SpanProtocol`, and both backends' concrete
`line_col` return values assignable to `LineColPosProtocol` — with **zero changes** to
`terminalsrc.py` or `fltk/_native/__init__.pyi`. Pyright resolves the mutual recursion
(`SpanProtocol` ↔ `LineColPosProtocol` via `line_span`/`line_col`) without issue.

Consequence — a deliberate refinement of `request.md`'s "touches exactly three hand-written
files": only `span_protocol.py` needs type changes. `terminalsrc.py` and the native `.pyi`
keep their concrete return annotations (`LineColPos`), which conform covariantly. Keeping them
concrete is strictly better for downstream consumers: code annotated against a concrete
backend keeps the precise nominal type (e.g. `PySpan.line_col().line_span` stays
`terminalsrc.Span`), avoiding exactly the annotation-widening churn CLAUDE.md forbids. All of
`request.md`'s substantive constraints (structural protocol in `span_protocol.py`, `line_span`
typed `SpanProtocol`, zero `fltk._native` names, stub-stability guard) are met.

### Changes to `fltk/fegen/pyrt/span_protocol.py`

1. **Add `LineColPosProtocol`** — a `@runtime_checkable` `Protocol` (mirroring
   `SpanProtocol`'s decoration) with three **read-only property** members:

   ```python
   @runtime_checkable
   class LineColPosProtocol(Protocol):
       @property
       def line(self) -> int: ...        # 0-based codepoint line index
       @property
       def col(self) -> int: ...         # 0-based codepoint column index
       @property
       def line_span(self) -> "SpanProtocol": ...  # covers the line, excl. trailing '\n'
   ```

   Docstrings state the semantics both backends already share (0-based codepoint indices;
   `line_span` excludes the trailing newline — matching `terminalsrc.LineColPos` and the
   native `.pyi` docs). **Property members are load-bearing**: plain protocol attributes are
   invariant, which would reject `terminalsrc.LineColPos.line_span: Span`; read-only
   properties permit the covariant match (dataclass field on the Python side, PyO3 getters on
   the native side). Also note in its docstring that `runtime_checkable` `isinstance` checks
   member presence only, as `SpanProtocol` already documents for itself.

   Placement: above `SpanProtocol` in the module (forward reference `"SpanProtocol"` in
   `line_span` handles the cycle; ordering is stylistic).

2. **Retype `SpanProtocol.line_col` / `line_col_or_raise`** to return
   `"LineColPosProtocol | None"` / `"LineColPosProtocol"`. Docstrings otherwise unchanged.

3. **Delete the `TODO(spanprotocol-native-linecol)` comment block** (`span_protocol.py:87-96`)
   — this change closes it.

4. **Preserve the `LineColPos` import surface.** `from fltk.fegen.pyrt.terminalsrc import
   LineColPos` becomes unused by annotations, but `span_protocol.LineColPos` has been an
   importable public name; out-of-tree consumers may import it from here. Keep it as an
   explicit re-export (redundant-alias form `from fltk.fegen.pyrt.terminalsrc import
   LineColPos as LineColPos`, or `# noqa: F401` — whichever satisfies ruff) with a
   backward-compatibility comment. `SpanKind` stays
   (still used by the `kind` member).

5. **`AnySpan` block untouched.** It remains the module's sole `fltk._native` reference,
   runtime-only, inside `try/except`, structurally separate from both protocols.

### Files that do NOT change

- `fltk/fegen/pyrt/terminalsrc.py` — `Span.line_col/line_col_or_raise` keep returning concrete
  `LineColPos`; the dataclass already conforms to `LineColPosProtocol` (probe-verified).
- `fltk/_native/__init__.pyi` — native `Span.line_col` keeps returning native `LineColPos`;
  its property-based `LineColPos` already conforms (probe-verified).
- Rust sources — no runtime behavior changes anywhere; this is a static-type-surface change
  plus tests.
- Generated artifacts — nothing regenerates. No generated file names `LineColPos`
  (exploration §6), and `SpanProtocol`'s member *names* are unchanged.
- `fltk/fegen/pyrt/error_formatter.py` — its `span.line_col_or_raise()` usage
  (`error_formatter.py:92-119`) touches only `.line`, `.col`, `.line_span.text()`, all present
  on `LineColPosProtocol`; it type-checks unchanged. `errors.py:131` uses the concrete
  `TerminalSource.pos_to_line_col`, unaffected.

### New stub-stability guard: `fltk/fegen/pyrt/test_span_protocol_native_free.py`

New test module (under `fltk/`, so inside pyright scope and the pytest run) asserting the
transitive property no existing test covers:

- Parse `span_protocol.py` with `ast`. Locate the `ClassDef` nodes for `SpanProtocol` and
  `LineColPosProtocol`; **fail if either is missing** (guards against silent rename breaking
  the guard).
- Assert no identifier, attribute chain, or string annotation anywhere within either class
  body contains `_native`.
- Assert the module's only `fltk._native` import is the runtime `AnySpan` fallback: every
  `import`/`ImportFrom` of `fltk._native` must sit inside a `Try` node, and none may appear
  under `if TYPE_CHECKING:` (a TYPE_CHECKING import is exactly the leak that would make the
  protocols stub-sensitive while remaining invisible at runtime).
- **Close the alias channel**: collect every name bound by any `fltk._native` import anywhere
  in the module (the `asname`-or-`name` of each import alias), and assert none of those names
  is referenced within either protocol class body — as an `ast.Name`, as the root of an
  attribute chain, or as an identifier token inside a string annotation. Without this, the two
  checks above have a joint gap: extending the existing legal try-import (`from fltk._native
  import Span as _RustSpan`, `span_protocol.py:120`) with e.g. `LineColPos as
  _RustLineColPos` and using the alias in a class-body annotation (`-> "_RustLineColPos |
  None"`) passes both — the import is try-enclosed, and the alias contains no `_native`
  substring — yet is exactly the stub-sensitivity leak the guard exists to catch (and would
  even work at runtime with the extension present, so it is a plausible accidental edit).
  Scoping the assertion to class bodies keeps the legitimate `AnySpan` use of `_RustSpan`
  below the classes legal.

This makes the D5.1 stability argument enforced rather than merely documented: if a future
edit makes either protocol's structural surface native-dependent, this test fails even though
the generated-file "names no native" scans cannot see it.

### Bookkeeping

- Remove the `## spanprotocol-native-linecol` entry from `TODO.md` (both paragraphs — the
  description and the "Constraint when closing this" paragraph; the constraint is discharged
  by the guard test).
- Update `test_span_protocol_assignability.py`'s module docstring: the "Native
  `fltk._native.Span` is deliberately NOT assigned..." paragraph (lines 14-17) inverts — the
  native static pin now exists and is the point.

## Edge cases / failure modes

- **Downstream code annotating protocol results with the concrete class** — e.g.
  `def f(s: SpanProtocol) -> LineColPos: return s.line_col_or_raise()` — newly fails pyright.
  Deliberate and correct: that annotation was already a runtime lie (a native span returns
  native `LineColPos`, which is not a `terminalsrc.LineColPos`). This is the only
  downstream-visible static change; consumers using the field triple (`line`/`col`/
  `line_span`) or annotating against a concrete backend are unaffected. No generated-artifact
  surface moves.
- **`reveal_type` shift**: `span.line_col()` on a `SpanProtocol`-typed span now reveals
  `LineColPosProtocol | None` instead of `terminalsrc.LineColPos | None`. The protocol exposes
  the complete public field triple; `__eq__`/`__hash__` remain available via `object`, so no
  attribute access that worked cross-backend before stops type-checking.
- **Pyright version drift**: the probe validated 1.1.402. If a future pyright
  changes recursive-protocol handling, the static pins in
  `test_span_protocol_assignability.py` fail loudly in `make check` — the failure mode is
  detection, not silent regression.
- **Guard brittleness**: an intentional future restructuring of `span_protocol.py` (e.g.
  moving `AnySpan`) will trip the guard test. Intended — the guard exists to force deliberate
  review of exactly such edits; its assertions are scoped (class bodies + import placement)
  rather than a whole-file text ban so legitimate non-structural edits don't trip it.
- **Runtime `isinstance` on `LineColPosProtocol`** checks member presence only (standard
  `runtime_checkable` limitation, same as `SpanProtocol`); documented in its docstring.
- **Pure-Python environments** (extension absent): the native static pin sits under
  `if _rust_available:` so it never executes without the extension, while pyright — which
  always sees the `.pyi` stub — still checks it. Runtime native tests keep the existing
  `skipif` pattern.
- **Empty-source `col == -1` corner case** (`terminalsrc.py:139`): runtime semantics
  untouched; `LineColPosProtocol` types `col` as `int`, imposing no new constraint.

## Test plan

TDD order: extend the pins first; confirm the native pin reproduces exploration §3's pyright
error against unmodified `span_protocol.py`; then apply the change and confirm `make check`
goes green.

1. **`fltk/fegen/pyrt/test_span_protocol_assignability.py` (extended)** — static pins
   (module-level annotated assignments, pyright-checked by `make check`):
   - `_native_span_slot: SpanProtocol = _fltk_native.Span(0, 1)` under `if _rust_available:`
     (pyright checks the branch body regardless of the runtime condition) — the headline
     assertion: native spans are statically conformant.
   - `LineColPosProtocol` pins for both backends: a `PySpan.with_source(...).line_col_or_raise()`
     result into a `LineColPosProtocol` slot, and a native `Span.line_col()` result into a
     `LineColPosProtocol | None` slot (native pin under the same guard).
   - Runtime tests: `isinstance(<py LineColPos>, LineColPosProtocol)` and
     `isinstance(<native LineColPos>, LineColPosProtocol)` (native case `skipif`-gated);
     plus exercising the new pins at runtime, mirroring the existing
     `test_pyright_checked_slots_construct` pattern.
2. **`fltk/fegen/pyrt/test_span_protocol_native_free.py` (new)** — the stub-stability guard
   described above (both-classes-found, native-free class bodies, native import confined to
   the `Try` fallback, no TYPE_CHECKING native import, no native-import-bound alias
   referenced in either class body).
3. **Regression**: full `uv run pytest` and `make check` pass with no changes to
   `test_cst_protocol.py`, `test_genparser.py`, `test_gsm2tree_rs.py`,
   `test_is_span_guard.py`, or any generated file — demonstrating the generated pipeline is
   untouched. `error_formatter.py` type-checks unmodified.

After implementation, `fltk._native.Span` not conforming to `SpanProtocol` is a `make
check`-detectable regression on every future edit — the "near-drop-in Rust backend" promise
made static and enforced.

## Open questions

None. The one judgment call — keeping concrete backend return annotations rather than
widening them to the protocol (refining `request.md`'s three-file touch count) — is resolved
by CLAUDE.md's prohibition on annotation churn plus the design-time pyright probe proving the
narrower change sufficient.
