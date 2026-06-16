# Exploration: Scope expansion — crate dedup, filename tracking, shared error formatter

Follows `./exploration.md` and `./design.md` (draft). Addresses the three areas raised in
`./notes-design-user.md`.

---

## A. Crate-layout dedup for `pos_to_line_col`

### A.1 Crate inventory and dependency edges

The workspace root (`Cargo.toml:1-3`) declares three members:
- `.` → `fltk-native` (`Cargo.toml:6`)
- `crates/fltk-cst-core` (`crates/fltk-cst-core/Cargo.toml:2`)
- `crates/fltk-parser-core` (`crates/fltk-parser-core/Cargo.toml:2`)

**Declared dependency edges (all in the workspace):**

| Crate | Depends on |
|-------|-----------|
| `fltk-native` (`src/lib.rs`) | `fltk-cst-core` (via `Cargo.toml:25`, `default-features = false`) |
| `fltk-parser-core` (`crates/fltk-parser-core/Cargo.toml:16`) | `fltk-cst-core` (`default-features = false`) |
| `fltk-cst-core` | no workspace dependencies |

`fltk-native` does **not** depend on `fltk-parser-core` (confirmed: no entry in
`Cargo.toml:23-25`).

Outside the root workspace, additional standalone crates (each with their own
`[workspace]` declaration, excluded from the root):

- `crates/fegen-rust/Cargo.toml:24-25`: `fltk-cst-core` + `fltk-parser-core` (both).
- `tests/rust_cst_fixture/Cargo.toml:23`: `fltk-cst-core` only (no `fltk-parser-core`).
- `tests/rust_parser_fixture/Cargo.toml:19-20`: `fltk-cst-core` + `fltk-parser-core`.
- `tests/rust_poc_cst/Cargo.toml:22`: `fltk-cst-core` only.

### A.2 Where `pos_to_line_col` and `LineColPos` live now

**Single location:** `crates/fltk-parser-core/src/terminalsrc.rs`.

- `LineColPos` struct: `terminalsrc.rs:19-23` (`pub struct` with `line: i64`, `col: i64`,
  `line_span: Span`).
- `TerminalSource::pos_to_line_col`: `terminalsrc.rs:180-228`. Takes `pos: i64`, returns
  `Option<LineColPos>`. Lazy-builds `line_ends: OnceLock<Vec<i64>>` (`terminalsrc.rs:46`).
  Bisect logic: `terminalsrc.rs:191-227`.
- Public re-export from crate root: `fltk-parser-core/src/lib.rs:27`:
  `pub use terminalsrc::{LineColPos, TerminalSource};`

**Not in `fltk-cst-core`.** `crates/fltk-cst-core/src/span.rs` defines `Span`,
`SourceInner`, `SourceText`, `SpanError` (`lib.rs:18`). No `LineColPos`, no line/col
logic.

### A.3 Why the design says the logic must be duplicated

The design (`design.md §1.4`) states: `fltk-native` depends only on `fltk-cst-core`; the
pyo3 `Span` is in `fltk-cst-core`; `pos_to_line_col` / `LineColPos` are in
`fltk-parser-core`. To add `line_col()` to the pyo3 `Span`, the logic must be reachable
from `fltk-cst-core`. Because `fltk-cst-core` cannot depend on `fltk-parser-core`
(that edge would create a cycle: `fltk-parser-core → fltk-cst-core → fltk-parser-core`),
the current design calls for re-implementing the bisect logic in `fltk-cst-core`.

### A.4 Options for single-location placement

**Option 1: Move `LineColPos` and the bisect logic down into `fltk-cst-core`.** `fltk-cst-core/src/span.rs` gains `LineColPos` and a free function (not a method on `TerminalSource`) implementing the bisect. `fltk-parser-core/src/terminalsrc.rs` removes its own `LineColPos` and the logic body, re-exports from `fltk-cst-core` via `use fltk_cst_core::LineColPos`. The public `fltk-parser-core` API is preserved at `lib.rs:27` — callers using `fltk_parser_core::LineColPos` continue to work because it re-exports. `TerminalSource` keeps its `line_ends` cache and its `pos_to_line_col` method, but the method body calls the shared function from `fltk-cst-core` rather than duplicating the bisect. Touch points: `terminalsrc.rs` (remove bisect body, keep `TerminalSource::pos_to_line_col` as a thin wrapper), `lib.rs:27` (no change to re-export), `span.rs` (add `LineColPos` + free fn). No change to `fltk-native/Cargo.toml` — the dependency edge already exists (`fltk-native → fltk-cst-core`).

**Option 2: Leave logic in `fltk-parser-core`; add `fltk-native → fltk-parser-core` dependency.** This breaks the current structural separation: `fltk-native` is a pyo3 cdylib that today deliberately avoids linking `fltk-parser-core` (no pyo3 in `fltk-parser-core`, but adding the dependency still pulls the crate into the cdylib link). Dependency edge direction is preserved (no cycle), but the separation intent is violated and the cdylib grows.

**Option 3: Extract a new third crate** (e.g., `fltk-source-core`) containing only `LineColPos` + bisect logic + `SourceText`/`SourceInner`. Both `fltk-cst-core` and `fltk-parser-core` depend on it. Mechanically correct but maximum disruption — moves `SourceInner`/`SourceText` which are already established pyo3-linked types.

**Dependency direction summary:**

```
fltk-cst-core   ←   fltk-parser-core
      ↑
  fltk-native
```

Moving the bisect logic down into `fltk-cst-core` (Option 1) respects this direction.
No new dependency edge is needed in any Cargo.toml.

### A.5 What a move would touch (Option 1 only)

- `crates/fltk-cst-core/src/span.rs`: add `pub struct LineColPos { pub line: i64, pub col: i64, pub line_span: Span }` and a pub free function `fn resolve_line_col(text: &str, pos: i64, line_ends: &OnceLock<Vec<i64>>) -> Option<LineColPos>` (or equivalent signature).
- `crates/fltk-cst-core/src/lib.rs:18`: add `LineColPos` to the `pub use span::` line.
- `crates/fltk-parser-core/src/terminalsrc.rs`: replace the `LineColPos` struct definition and the bisect body with `use fltk_cst_core::LineColPos;` and a call to the shared function from `fltk-cst-core`. The `TerminalSource::pos_to_line_col` method stays, but its body calls the shared function. `OnceLock<Vec<i64>> line_ends` stays on `TerminalSource`.
- `crates/fltk-parser-core/src/lib.rs:27`: `pub use terminalsrc::{LineColPos, TerminalSource};` — unchanged, still re-exports `LineColPos` for downstream.
- No `Cargo.toml` changes in the workspace (the `fltk-parser-core → fltk-cst-core` dependency already exists at `crates/fltk-parser-core/Cargo.toml:16`).
- Existing inline tests in `terminalsrc.rs:424-519` stay where they are — they test `TerminalSource::pos_to_line_col`, which still exists as a method.
- New `fltk-cst-core/src/lib.rs` tests would test the shared free function directly.

---

## B. Filename tracking on `TerminalSource` / `SourceText` / `SourceInner`

### B.1 Python `SourceText` construction sites

`fltk/fegen/pyrt/terminalsrc.py:9-21`:
```python
@dataclass(frozen=True, slots=True)
class SourceText:
    _text: str
    def __init__(self, text: str) -> None:
        object.__setattr__(self, "_text", text)
```
Constructor takes only `text: str`. No `filename` parameter.

**Where `SourceText` is constructed:**
- Generated parsers: `fltk/fegen/fltk_parser.py:16` (and all generated parsers):
  `self._source_text = fltk.fegen.pyrt.span.SourceText(text=terminalsrc.terminals)`.
  The `terminalsrc` arg is a `TerminalSource` passed to `Parser.__init__`.
- `gsm2parser.py:105-130`: the IIR init expression for `_source_text` (line 107-118) is
  `SourceText(text=terminalsrc.terminals)`. This is what generates the above line.
  `terminalsrc` is the constructor parameter at line 121-127.

**Where `TerminalSource` is constructed** (the handoff point):
- `terminalsrc.py:163-166`: `TerminalSource.__init__(self, terminals: str)` — only `terminals`.
- Clockwork `clockwork/dsl/ir/parse.py:28`: `terminalsrc.TerminalSource(source_file.read())` (from file read).
- Clockwork `clockwork/dsl/ir/parse.py:33`: `terminalsrc.TerminalSource(source)` (from string, with separate `filename` arg to `terminals_to_cst`).
- Clockwork `clockwork/dsl/ir/parse.py:41`: similarly.

`filename` in clockwork's `terminals_to_cst` (`parse.py:44-46`) is passed separately from
`terminals` — it is not stored on `TerminalSource` or `SourceText` today.

### B.2 Rust `SourceText` construction sites

`crates/fltk-cst-core/src/span.rs`:
- `SourceText::from_str(text: &str) -> Self` (`span.rs:65`): takes only `text`.
- `SourceText::new(text: &str) -> Self` (pyo3 `#[new]`, `span.rs:88`): takes only `text`.

`SourceInner` struct (`span.rs:46-48`): `pub struct SourceInner { pub(crate) text: String }`. No `filename` field.

`TerminalSource::new(text: &str)` (`terminalsrc.rs:51`): calls `SourceText::from_str(text)` then `Self::from_source_text(source)`.
`TerminalSource::from_source_text(source: SourceText)` (`terminalsrc.rs:56`): only `source`.

### B.3 pyo3 stub (`fltk/_native/__init__.pyi`)

`__init__.pyi:23`: `def __init__(self, text: str) -> None: ...`

No `filename` parameter.

### B.4 Where each construction site would change for optional filename

Filename belongs on `SourceText`/`SourceInner` so it is carried by every span created from that source. Adding `filename: str | None = None`:

| Site | File:line | Change |
|------|-----------|--------|
| Python `SourceText.__init__` | `terminalsrc.py:20` | Add `filename: str \| None = None` param; `object.__setattr__(self, "_filename", filename)` |
| Python `SourceText` dataclass field | `terminalsrc.py:9-21` | Add `_filename: str \| None` field |
| Python `TerminalSource.__init__` | `terminalsrc.py:163` | Add `filename: str \| None = None` param; thread into `SourceText` construction (but `TerminalSource` does not construct `SourceText` — the generated parser does) |
| Generated parser `Parser.__init__` | generated (`fltk_parser.py:14-16`) | `self._source_text = SourceText(text=terminalsrc.terminals, filename=???)` — the generated parser has no access to filename; caller would need to set filename on `terminalsrc` OR pass it some other way |
| gsm2parser IIR init for `_source_text` | `gsm2parser.py:107-118` | Currently `SourceText(text=terminalsrc.terminals)` — to thread filename, either `TerminalSource` carries it (and it is accessed here) or a new parser constructor param is added |
| Rust `SourceInner` | `span.rs:46-48` | Add `pub(crate) filename: Option<String>` |
| Rust `SourceText::from_str` | `span.rs:65` | Add `filename: Option<&str>` param; break all callers |
| Rust `SourceText::new` (pyo3 `#[new]`) | `span.rs:88` | Add `filename: Option<&str>` param with default `None` |
| Rust `TerminalSource::new` | `terminalsrc.rs:51` | Add `filename: Option<&str>` param; pass through `SourceText::from_str` |
| Rust `TerminalSource::from_source_text` | `terminalsrc.rs:56` | `SourceText` already constructed externally — filename must be set before or on `SourceText` |
| pyi stub `SourceText.__init__` | `fltk/_native/__init__.pyi:23` | `def __init__(self, text: str, filename: str \| None = None) -> None: ...` |

**The key threading constraint:** generated parsers construct `_source_text` from `terminalsrc.terminals` in their `__init__`. Today the `TerminalSource` is the caller's entry point. The cleanest path for filename:
- Add `filename: str | None = None` to Python `TerminalSource.__init__` (`terminalsrc.py:163`).
- Store it as `self.filename: str | None = filename`.
- The generated parser init IIR expression (`gsm2parser.py:107-118`) would become `SourceText(text=terminalsrc.terminals, filename=terminalsrc.filename)` — requires the IIR generator to read the `filename` attribute off the `terminalsrc` field.

**Span → filename reach:** a `Span` reaches its source via `self._source` (Python) / `self.source: Option<Arc<SourceInner>>` (Rust). If `SourceInner` carries `filename`, then `span.source.as_ref().and_then(|s| s.filename.as_deref())` gives the filename. No per-span storage needed.

**Optionality is feasible end-to-end:** callers that pass no `filename` get `None` everywhere. Neither the parser nor the span logic branches on filename — it is stored and retrieved, never interpreted by the runtime. `TerminalSource("my source")` keeps working; `TerminalSource("my source", filename="foo.clk")` adds the optional info.

### B.5 `SourceText` vs `TerminalSource` as the natural filename carrier

The `TerminalSource` is constructed by the *caller* and is the natural place for caller-provided metadata. `SourceText` is constructed by the generated parser from `TerminalSource.terminals`. So the call chain is:

```
caller: TerminalSource(text, filename=...) → Parser(terminalsrc) → _source_text = SourceText(text, filename=terminalsrc.filename) → Span carries Arc<SourceInner{text, filename}>
```

On the Rust backend the Rust `TerminalSource` (`terminalsrc.rs:38-47`) is internal to generated Rust parsers and does not surface to Python. There is no pyo3 `TerminalSource`. For the Rust path, the caller constructs `SourceText` directly (pyo3 `__init__`) and hands it to the generated Rust parser. So the Rust entry point for filename is `SourceText(text, filename=None)` — the pyo3 constructor.

---

## C. Shared error-formatter function

### C.1 Clockwork's `format_line_with_error` — exact anatomy

File: `clockwork/dsl/ir/cst_util.py:70-92`.

```python
def format_line_with_error(span: Span, terminals: TerminalSource, module_id: ModuleID | None) -> str:
    module_path = "(unknown location)"
    if module_id is not None and module_id.name:
        module_path = ""
        if module_id.repo:
            module_path += f"@{module_id.repo}: "
        module_path += str(module_id.get_base_path())

    line_col = terminals.pos_to_line_col(span.start)
    return (
        f"\nIn {module_path}:{line_col.line + 1}:{line_col.col + 1}:\n"
        f"{get_span(line_col.line_span, terminals)}\n"
        f"{' ' * line_col.col}^\n"
    )
```

**Inputs:**
- `span: Span` — concrete `terminalsrc.Span` (reads `span.start`, which is NOT on `SpanProtocol`).
- `terminals: TerminalSource` — used twice: (1) `terminals.pos_to_line_col(span.start)` to get `line_col`; (2) passed to `get_span(line_col.line_span, terminals)` as a fallback because today's Python `LineColPos.line_span` is **sourceless** (`terminalsrc.py:197-200` constructs `Span(start, end)` with `_source=None`).
- `module_id: ModuleID | None` — clockwork-specific identifier (`module_id.name`, `module_id.repo`, `module_id.get_base_path()`). This is NOT a bare filename.

**Outputs:** a string with the format:
```
\nIn <path>:<line+1>:<col+1>:\n
<line text>\n
<col spaces>^\n
```

Line numbers are **1-based** in the output (`line_col.line + 1`, `line_col.col + 1` for the header) but the caret indent uses **0-based** `col` (`' ' * line_col.col`).

**`get_span` usage** (`cst_util.py:19-48`): tries `span.text()` first; if `None` and `terminals` is provided, falls back to `terminals.terminals[span.start:span.end]` (direct index into raw string). The comment at line 46 calls this the "sourceless line_span residual." With the new design, `line_span` would be source-bearing, eliminating the `terminals` fallback for this path.

**`ModuleID`** (`clockwork/dsl/ir/module_id.py:16-53`): clockwork-specific dataclass with `repo: str`, `name: str`, `suffix`. `get_base_path()` returns a `Path`. This is not a plain filename string; it encodes clockwork's Bazel repo-relative module path.

**Call-site pattern in clockwork:** `format_line_with_error` is called ~20 times in clockwork (confirmed by grep above). Every call passes a `span` (concrete `terminalsrc.Span`), `module.terminals` (a `TerminalSource`), and `module.module_id` (a clockwork `ModuleID`). The function always returns a string that callers prepend or append to an error message.

### C.2 What an fltk-provided equivalent would need

The clockwork `format_line_with_error` has two concerns:
1. **Line/col resolution + line-text + caret formatting** — generic, reusable by any FLTK consumer.
2. **Filename/path rendering** — clockwork-specific (`ModuleID.repo`, `ModuleID.get_base_path()`). A generic fltk version would take a plain `str | None` filename, not a `ModuleID`.

If the new design adds (a) `SpanProtocol.line_col()` returning a source-bearing `LineColPos`, and (b) optional `filename` on `SourceText`/`SourceInner`, then a generic fltk formatter could:

```python
def format_error_context(span: SpanProtocol, message: str) -> str:
    lc = span.line_col_or_raise()
    filename = ...  # reached how?
    header = f"In {filename}:{lc.line + 1}:{lc.col + 1}:" if filename else f"At line {lc.line + 1}, col {lc.col + 1}:"
    line_text = lc.line_span.text() or ""  # source-bearing after the new design
    return f"\n{header}\n{line_text}\n{' ' * lc.col}^\n{message}\n"
```

**What fltk already has (after the in-progress design):**
- `span.line_col()` / `span.line_col_or_raise()` → `LineColPos(line, col, line_span)` (new, from design.md).
- `lc.line_span.text()` → the full line text (source-bearing `line_span`, new in the design).
- `lc.line` + 1, `lc.col` + 1 for 1-based display; `lc.col` raw for caret indent.

**What is missing for a generic formatter:**
- Filename: not yet on `SourceText`/`SourceInner`; this is area B above.
- A way to reach the filename *from a span*. If `SourceInner` carries `filename: Option<String>` and `Span.source` is `Option<Arc<SourceInner>>`, a new `Span.filename() -> str | None` method (or `SpanProtocol.filename()`) would expose it without adding it to the formatter's signature.

**Natural placement in fltk:** `fltk/fegen/pyrt/terminalsrc.py` or a new `fltk/fegen/pyrt/errors.py`. The function would be a free function (not a method), taking `span: SpanProtocol` and `message: str`, with filename reached via `span.filename()` (or a `filename: str | None = None` override parameter for callers who want to supply it separately, e.g. before filename tracking lands on `SourceText`). It would be importable by clockwork and any other out-of-tree consumer. No clockwork-specific dependencies (`ModuleID`) would appear in it.

**How clockwork would migrate:** replace `format_line_with_error(span, terminals, module_id)` with the fltk function, passing `filename=str(module_id.get_base_path()) if module_id and module_id.name else None`. The `terminals` argument disappears (no longer needed as the `get_span` sourceless fallback, because `line_span` is now source-bearing). The `span` annotation migrates from `terminalsrc.Span` to `SpanProtocol`.

**Blocking dependency on area B:** the formatter can be written without filename-on-span (taking an explicit `filename: str | None` parameter), decoupling it from area B. Filename-on-span makes it more ergonomic (no explicit `filename` arg at call site) but is not a prerequisite for the formatter to exist.

### C.3 Clockwork's existing error-position formatter (parse error path)

`clockwork/dsl/ir/parse.py:59-61`:
```python
error_linecol = terminals.pos_to_line_col(backend.error_position())
msg = f"In {filename}:{error_linecol.line + 1}:{error_linecol.col + 1}:\n"
msg += backend.error_text(terminals.terminals)
```
This is a separate code path (parse failure, not IR semantic error) with no caret — it uses `pos_to_line_col` directly on `terminals` and formats manually. The fltk helper would not automatically subsume this path unless the helper also accepts a raw position.

---

## Open factual questions

1. **Rust `TerminalSource` access for filename:** the Rust `TerminalSource` (`terminalsrc.rs:38-47`) is not a pyo3 class; it is internal to generated Rust parsers. The Rust entry point for caller-provided filename is the pyo3 `SourceText` constructor (`span.rs:88`). There is no Rust-side `TerminalSource` constructor exposed to Python callers. The threading differs between backends: Python callers pass filename to `TerminalSource`, which the generated parser extracts into `SourceText`; Rust callers would pass filename directly to `SourceText`.

2. **`SourceText` mutability (Python):** `SourceText` is a `frozen=True, slots=True` dataclass (`terminalsrc.py:8`). Adding `_filename: str | None` as a field with a default is straightforward for a frozen dataclass; construction `SourceText(text="...", filename="foo.py")` (via `__init__` override pattern already in place at line 20-21) works.

3. **Arc immutability for filename (Rust):** `SourceInner` is shared via `Arc` (read-only after construction). Adding `filename: Option<String>` to `SourceInner` (`span.rs:46-48`) requires it to be set at construction time — the same constraint as `text`. This is satisfied: `SourceText::from_str` and `SourceText::new` are the construction points.

4. **`format_line_with_error` vs `format_error_context` naming:** the clockwork name `format_line_with_error` includes the module-path formatting. A generic fltk version would not contain module-path logic (that stays in clockwork). The generic function would need a different name to avoid confusion.
