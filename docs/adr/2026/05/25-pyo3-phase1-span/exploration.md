# Phase 1 Exploration: Span / TerminalSource Rust Design

Concise. Precise. No padding. Audience: smart human/LLM implementing Phase 1.

---

## 1. Current Python `Span` — Exact Definition

`fltk/fegen/pyrt/terminalsrc.py:7-15`:
```python
@dataclass(frozen=True, eq=True, slots=True)
class Span:
    """Span of elements in the range [start, end)"""
    start: int
    end: int

UnknownSpan: Final = Span(-1, -1)
```

`int` in Python is arbitrary-precision; `i64` in Rust covers all practical source file sizes.

`Span` is also used for internal sentinels: `Span(-1, -1)` is `UnknownSpan`, and the parser sets `span.end = -1` as a "not yet closed" marker (`fltk_parser.py` pattern: `Grammar(span=Span(start=pos, end=-1))` then later `result.span = Span(start=result.span.start, end=pos)`). So negative values are real inputs, not errors.

---

## 2. `Span` Construction Sites — The Hot Path

The phase plan's statement about positional construction is confirmed:

- `terminalsrc.py:38`: `return Span(pos, pos + len(literal))` — positional, 2-arg.
- `terminalsrc.py:43`: `return Span(pos, match.end())` — positional, 2-arg.
- `fltk_parser.py`: ~80 positional construction sites (pattern: `Span(start=pos, end=-1)` uses keyword args, then `Span(start=result.span.start, end=pos)` also uses keyword args). The generated parser uses keyword args throughout, not pure positional, but positional must also work to match `terminalsrc.py`.
- `bootstrap_parser.py`: same pattern.

Both positional (`Span(1, 2)`) and keyword (`Span(start=1, end=2)`) construction are required. PyO3 `#[new]` supports both naturally.

---

## 3. `Span` Usage Patterns — Exhaustive

### 3a. As a node field
Every CST node has `span: Span` (mutable on the node — the node is not frozen). The parser writes it twice per node.

- Read: `result.span.start` — e.g., `fltk_parser.py` `Span(start=result.span.start, end=pos)`.
- Write: `result.span = Span(...)` — replaces the span object, does not mutate it (Span is frozen).

### 3b. As a child value in `children` lists
Leaf terminals (literals, regexes, whitespace separators in trivia rules) are stored as bare `Span` objects in node `children` lists. `fltk_cst.py:172-...` `Items` class: child union is `Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span`. This means a `Span` can appear as `children[i][1]` and be operated on directly.

### 3c. Source text slicing
Text is never stored in the CST. Text recovery always goes through `terminals[span.start : span.end]`.

Confirmed call sites:
- `bootstrap2gsm.py:24`: `self.terminals[span.start : span.end]` — `self.terminals` is a `str` passed to the visitor constructor.
- `fltk2gsm.py:24`: same pattern.
- `unparse/pyrt.py:33-35`: `extract_span_text(span: Span, terminals: str) -> str: return terminals[span.start : span.end]`

The generated unparser calls `pyrt_module.method.extract_span_text.call(span_expr, iir.SelfExpr().fld.terminals.load())` (`gsm2unparser.py:1804-1806`). The unparser stores `terminals: str` as a field set in `__init__` (`gsm2unparser.py:182-191`), passed from `plumbing.unparse_cst(unparser_result, cst, terminals: str, ...)` which receives it from the caller as a plain string.

### 3d. Equality and hash
- `Span` is used as a dict key nowhere found in production code.
- Equality (`==`) is used in tests: `test_gsm2parser.py:74` compares `ApplyResult` which contains CST nodes which contain `Span` values — recursive dataclass equality.
- `__hash__` is needed on `Span` because it has `frozen=True` in the Python dataclass (Python auto-generates `__hash__` for frozen dataclasses). Whether any code actually hashes `Span` objects is unconfirmed, but the contract must be preserved.

### 3e. `isinstance` check on Span
`gsm2unparser.py:983`: emits `iir.IsInstance(expr=child_value, typ=span_type)` — `isinstance(child, Span)`. This is in the generated unparser's dispatch logic to distinguish terminal spans from node objects.

---

## 4. TerminalSource — Current Python Design

`terminalsrc.py:25-68`:
```python
class TerminalSource:
    def __init__(self, terminals: str):
        self.terminals: Final = terminals       # the full source text
        self.terminals_len: Final = len(terminals)
        self.line_ends: list[int] = []          # lazily computed

    def consume_literal(self, pos: int, literal: str) -> Span | None: ...
    def consume_regex(self, pos: int, regex: str) -> Span | None: ...
    def pos_to_line_col(self, pos: int) -> LineColPos: ...
```

`TerminalSource` holds the source text. The parser holds a `TerminalSource`. CST nodes hold only `Span` — no reference to the source.

### TerminalSource ownership chain in current design

```
plumbing.parse_text(parser_result, text, ...) -> ParseResult
  -> terminals = TerminalSource(text)          # created here, owned locally
  -> parser = parser_result.parser_class(terminals)
  -> result = parser.apply__parse_{rule}(0)
  -> ParseResult(result.result, text, ...)     # cst returned; terminals goes out of scope
```

`ParseResult` (`plumbing_types.py:25-32`):
```python
@dataclass
class ParseResult:
    cst: Any | None
    terminals: str         # the raw string, not TerminalSource
    success: bool
    error_message: str | None
```

`ParseResult` carries the raw `terminals: str`, not the `TerminalSource`. So users who want source text must reconstruct `TerminalSource` themselves, or use `terminals` directly for slicing.

The unparser receives `terminals: str` (not `TerminalSource`) as a constructor argument (`gsm2unparser.py:182-191`), and `plumbing.unparse_cst` passes `terminals: str` (`plumbing.py:283,298`).

Error formatting (`errors.format_error_message`) receives `terminals: terminalsrc.TerminalSource` (`errors.py:54`) — the full `TerminalSource` object, for `pos_to_line_col`. This is called inside the parsing stage before `TerminalSource` goes out of scope.

### The Python design's problem (user's stated concern)

CST nodes carry only `Span(start, end)` — no reference to the `TerminalSource`. User applications must pair CST nodes with the source text externally (e.g., in a "compiler context" object). There is no way to get the source text from a CST node alone. `errors.py:format_error_message` itself requires `TerminalSource` passed separately.

---

## 5. The TerminalSource-as-Rust-type Question

Phase 1's stated scope is only `Span`. But the user's concern is that the Rust design for `Span` should be shaped with `TerminalSource` in mind, because the two are coupled: `Span` is a view into a `TerminalSource`'s text, but currently carries no reference to it.

### What would a "better" API look like (facts only, no prescription)

A `Span` that carries an `Arc<str>` (or `Rc<str>`) reference to the source text would allow `span.text()` to return the slice without any external context. This is the design used by, e.g., `rowan` (Rust CST library) and `logos` (lexer). The cost is 16 bytes of `Arc<str>` overhead per `Span` (pointer + strong count reference) vs. 8 bytes for the current `(start: i32, end: i32)` representation.

A `Span` that carries a raw `*const u8` pointer into the backing string (unsafe, zero overhead beyond the pointer) is another option, requiring the source string to be pinned.

The current Python `Span(start=int, end=int)` is 2 integers. PyO3 `#[pyclass(frozen)]` with `start: i64, end: i64` is the direct replacement — 16 bytes on the Rust side.

### Synthetic nodes

The user specifies a real constraint: automated refactoring tools create synthetic CST nodes that are either (a) sourceless (generated, no source text) or (b) have their own private `TerminalSource` representing their text. These synthetic nodes are unparsed to produce new source text. The design must handle:
- `Span` with a reference to a real parsed source.
- `Span` with a reference to a synthetic/private source.
- `Span` with no source at all (e.g., `UnknownSpan` on newly constructed nodes).

---

## 6. API Compatibility Constraints — Exact

The Python API that must remain compatible:

### From Python callers of `Span`:
- `Span(start, end)` — 2-arg positional construction.
- `Span(start=s, end=e)` — keyword construction.
- `span.start` — integer read.
- `span.end` — integer read.
- `span == other_span` — value equality.
- `hash(span)` — hashable (even if no production code currently hashes spans).
- `repr(span)` — some representation (used in logging).
- `isinstance(x, Span)` — type check in generated unparser.
- `terminals[span.start : span.end]` — span as slice indices into a `str`.

### From Python callers of `TerminalSource`:
- `TerminalSource(text: str)` — construction from string.
- `terminalsrc.consume_literal(pos, literal) -> Span | None`.
- `terminalsrc.consume_regex(pos, regex) -> Span | None`.
- `terminalsrc.terminals` — the raw string attribute (accessed in error formatting: `terminals.terminals[...]`).
- `terminalsrc.pos_to_line_col(pos) -> LineColPos` (used in `errors.format_error_message`).
- `terminalsrc.terminals_len` — length (used in `plumbing.py:173`: `result.pos != len(terminals.terminals)`; actually uses `len()` on `.terminals` string, not `terminals_len` directly).

### Import paths that must continue to work:
- `fltk.fegen.pyrt.terminalsrc.Span`
- `fltk.fegen.pyrt.terminalsrc.UnknownSpan`
- `fltk.fegen.pyrt.terminalsrc.TerminalSource`

The re-export pattern (replacing definition with `from fltk._native import Span`) keeps all import paths working.

---

## 7. Two-API Design Constraints (user's requirement)

The user requires both:

**Compatible API**: `Span(start, end)` with no source reference — matches existing Python code. Callers slice source text manually via `terminals[span.start : span.end]`.

**Better API**: `Span` (or a related type) that carries a reference to its source text and exposes `span.text()` or similar without needing external context. This API should not break callers that don't use it.

The "better" API must handle three span states:
1. Span with reference to a parsed `TerminalSource` (normal parsed nodes).
2. Span with reference to a private/synthetic `TerminalSource` (synthetic nodes from refactoring tools).
3. Span with no source (freshly constructed node, `UnknownSpan`).

### Factual design options (not prescriptions)

**Option A: Extend `Span` with optional source ref.** `Span` gains an optional `Arc<str>` (or PyO3 `Option<Py<PyAny>>`) field. Default is `None`. Constructor `Span(start, end)` produces sourceless span (backward-compatible). A new constructor or factory method `Span.with_source(start, end, source)` produces source-bearing span. `.text()` returns `Option<&str>`.

**Option B: Two types — `Span` (backward-compatible) and `SourceSpan` (new).** `Span` stays as `(start, end)` pair. `SourceSpan(span, source)` wraps a `Span` with a reference. Python code can use `Span` for backward compatibility; new code can use `SourceSpan`. Generated parser can produce `SourceSpan` when a source is known.

**Option C: Attach source to `TerminalSource`, not to `Span`.** `TerminalSource` gains a registry so `span.resolve(terminal_source)` can extract text. No change to `Span` struct at all. "Better" API is: call `terminal_source.text(span)` instead of `terminals[span.start:span.end]`. This is exactly the current API, with a method name instead of subscript syntax.

---

## 8. Phase 1 Declared Scope (from phase-plan.md)

Phase 1 scope per `phase-plan.md:44-56`:
- Implement `Span` as `#[pyclass(frozen)]` with `#[pyo3(get)] start: i64`, `#[pyo3(get)] end: i64`.
- `#[new]` accepting positional and keyword args.
- `__richcmp__` (Eq), `__hash__`, `__repr__`.
- `UnknownSpan` as module-level constant `Span(-1, -1)`.
- Replace `Span` definition in `terminalsrc.py` with import from `fltk._native`.
- Full test suite must pass.

Phase 1 does **not** include `TerminalSource` replacement — that is not mentioned as in scope. But the user's concern is that `Span`'s Rust struct shape should anticipate the `TerminalSource` design to avoid throwaway work.

---

## 9. What the Span Rust Struct Must Support — Minimal Contract

Based on all usages:

1. `start: i64` and `end: i64` as readable attributes from Python. Negative values (`-1`) are valid.
2. `__new__` accepting `(start, end)` positionally or as keywords.
3. `__richcmp__` implementing `==` with value equality `(start, end)`.
4. `__hash__` consistent with `==`.
5. `__repr__` (any reasonable format; Python dataclass emits `Span(start=1, end=2)`).
6. Frozen (immutable) — no setters on `start`/`end`.
7. Module-level constant `UnknownSpan = Span(-1, -1)`.
8. Importable as `fltk.fegen.pyrt.terminalsrc.Span` (via re-export from `terminalsrc.py`).

The Rust struct does **not** need to store source text to satisfy Phase 1's defined scope. The question is whether the struct layout should reserve space for an optional source ref now vs. adding it later (a breaking change to the Rust internal layout, though not to the Python API).

---

## 10. Current Build Infrastructure (Phase 0 Output)

`src/lib.rs:1-22`:
```rust
use pyo3::prelude::*;

#[pyclass]
struct Ping;

#[pymethods]
impl Ping {
    #[new]
    fn new() -> Self { Ping }
    fn pong(&self) -> &str { "pong" }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Ping>()?;
    Ok(())
}
```

`Cargo.toml`: `pyo3 = { version = "0.23", features = ["abi3-py310"] }`.

Phase 1 adds `Span` to `_native` module. Submodule structure (e.g., `fltk._native.terminalsrc`) is not yet established; Phase 1 could add directly to `_native` or add a submodule. The re-export in `terminalsrc.py` hides the internal module path from all callers.

---

## 11. Open Factual Questions

1. **`Span` in `LineColPos`**: `terminalsrc.py:18-22` defines `LineColPos(line, col, line_span: Span)`. `pos_to_line_col` returns this. If `TerminalSource` is later replaced with a Rust type, `LineColPos` (currently a Python dataclass) would need compatible `Span` in `line_span`. Phase 1 only replaces `Span`, so `LineColPos` using the Rust `Span` works naturally once `Span` is imported from `_native`.

2. **`Span` pickling**: No evidence of `Span` being pickled anywhere. Not a constraint unless test infrastructure requires it.

3. **Thread safety**: PyO3 `#[pyclass(frozen)]` is `Send + Sync` by default. No evidence of cross-thread CST usage in current codebase, but `Arc<T>` in a future source-bearing span would require the source to be `Send + Sync`.

4. **Source text encoding**: Current `TerminalSource.terminals` is a Python `str` (Unicode). `span.start`/`span.end` are character indices (not byte offsets), because `consume_regex` uses Python's `re.match` which operates on character positions, and `terminals[span.start : span.end]` is character-indexed. Any Rust replacement of `TerminalSource` must match this: UTF-8 byte indices would not be compatible with Python `str` slicing unless conversion is done at the boundary.

5. **`terminals_len` attribute**: `TerminalSource.terminals_len: Final = len(terminals)` (`terminalsrc.py:29`). Direct access to this attribute is not found in non-test code (confirmed: `plumbing.py:173` uses `len(terminals.terminals)`, not `terminals.terminals_len`). It's an internal optimization cache, not a required API surface.

6. **`TerminalSource` in generated parser field**: `gsm2parser.py:61-67` registers `TerminalSource` as an IIR type with module `fltk.fegen.pyrt.terminalsrc`. The generated parser declares `self.terminalsrc: TerminalSource`. If `TerminalSource` stays a Python class (not replaced in Phase 1), no impact. If later replaced with a Rust type, the IIR type registration at `gsm2parser.py:61-67` and `context.py` would need updating.
