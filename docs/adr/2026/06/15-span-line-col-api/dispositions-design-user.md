# Dispositions — user comments on the line/col design gate

Source: `./notes-design-user.md` (authoritative user comments).
Design revised in place: `./design.md`.

---

user-1 (single-location line/col logic — stop duplicating `pos_to_line_col`):
- Disposition: Fixed
- Action: Replaced the prior draft's "re-implement the bisect in `fltk-cst-core` and flag the
  duplication as a forced compromise" with a **move-down**: `LineColPos` and the bisect become a single
  shared `resolve_line_col` free function in `fltk-cst-core/src/span.rs`; `fltk-parser-core` deletes its
  own `LineColPos` (`terminalsrc.rs:18-23`) and re-exports the moved type, keeping
  `fltk_parser_core::LineColPos` (`lib.rs:27`) verbatim so no downstream Rust consumer churns;
  `TerminalSource::pos_to_line_col` becomes a thin wrapper over the shared function; the pyo3 `Span` and
  the pure-Rust `Span::line_col_inner` call the same function. Written up in design §1.4 (dependency
  graph + why it's possible), §2.5 (target state, exploration §A.4 Option 1 / §A.5), §2.6
  (pyo3/registration), §7 (the compromise is removed; rejected alternatives — new Cargo edge, third
  crate — recorded). Edges verified: `fltk-parser-core → fltk-cst-core` already exists with
  `default-features = false` (`crates/fltk-parser-core/Cargo.toml:16`), so no new Cargo edge and no
  cycle; the pyo3 `pyclass` attribute is invisible to `fltk-parser-core` (it never links pyo3).
- Severity assessment: Without this, the algorithm lives in two Rust copies that can silently diverge on
  multibyte/EOF/empty-source edges — exactly the cross-backend-equivalence failure the whole feature
  exists to prevent. The user explicitly required one copy and authorized moving code; a single shared
  function removes the divergence surface entirely.

user-2 (scope expansion — optional filename tracking + a shared error formatter):
- Disposition: Fixed
- Action — 2a (filename): Added an **optional** `filename` stored **once** on the source allocation
  (`SourceInner.filename: Option<String>`, Python `SourceText._filename`), caller-provided at
  construction, never per-span, optional end-to-end (filename-less sources still parse). Threading
  specified at every site (design §2.8, from exploration §B): Rust `SourceInner` / `SourceText::from_str`
  / `SourceText::new` (pyo3 `#[new]`, `None` default) / `TerminalSource::new`; Python `SourceText`
  dataclass + `__init__` / `TerminalSource.__init__`; the generated Python parser's `_source_text`
  construction (`gsm2parser.py:107-118`) threads `terminalsrc.filename` — which **requires a regen**,
  honestly flagged (§2.8, §2.12, §4.6, §5) as the one departure from the prior "no regen" claim. Surfaced
  via `SpanProtocol.filename() -> str | None` (§2.3) reading through the carried source; cross-backend
  result equivalence asserted (§2.9, §4.1). Existing `SourceText(text)` / `TerminalSource(text)` callers
  keep working via the `None` default; in-tree Rust `SourceText::from_str` callers add a `None` argument.
  Action — 2b (formatter): Added one fltk public function `format_source_line(span: SpanProtocol,
  message: str, *, filename: str | None = None) -> str` in a new module
  `fltk/fegen/pyrt/error_formatter.py` (not the existing `pyrt/errors.py`, which is the parser
  `ErrorTracker`). It reproduces clockwork's `format_line_with_error` shape (header + source line + caret
  + message), built from `line_col_or_raise()` + source-bearing `line_span.text()` + `filename`
  (explicit arg wins over `span.filename()`); no clockwork `ModuleID` dependency. Design §2.10; tests
  §4.5; clockwork migration path spelled out. Reconciled the efficiency claims with
  exploration-codepoint-efficiency (Rust `pos_to_line_col` is already `OnceLock`-cached and amortized
  O(log N_lines), codepoint→byte O(1), residual O(N) only in `Span::text()` — §2.6.3, §7). Open
  questions restated with defaults and resolution status (§6); the empty-source caret corner reconciled
  between §2.10 and OQ2.
- Severity assessment: Filename and a shared formatter are the two concrete things blocking the clockwork
  port from dropping its hand-rolled `format_line_with_error` and `get_span(..., terminals)` workaround;
  without them every out-of-tree consumer reimplements caret formatting and has no way to report a span's
  file. The forced regen and the two-line-ends-tables state duplication are the only residual costs, both
  flagged with paired-TODO plans (§7); neither is a duplicated algorithm.
