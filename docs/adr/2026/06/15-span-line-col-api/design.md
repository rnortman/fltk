# Design: cross-backend line/column + filename + error formatter on the span surface

Status: draft (design gate — API shape pending user approval)
Branch: `span-line-col-api`  Base: `8cd6232`
Exploration: `./exploration.md`, `./exploration-scope-expansion.md`, `./exploration-codepoint-efficiency.md`
Requirement: this ADR directory's task brief + `./notes-design-user.md` (authoritative user comments).

This revision incorporates two user comments on the prior draft:

1. **Single-location line/col logic.** The prior draft duplicated `pos_to_line_col` across two Rust
   crates and flagged it as a forced compromise. The user rejects the duplication and is willing to
   **move** code to get one copy. We now move `LineColPos` + the bisect logic *down* into
   `fltk-cst-core` (§2.5, §7); the compromise is gone.
2. **Scope expansion: filename tracking + a shared error formatter.** Add an optional `filename`
   carried once on the source allocation (`SourceText`/`SourceInner`/`TerminalSource`), surfaced so a
   span can report its file (§2.8, §2.9). Add one fltk public function that does what clockwork's
   `format_line_with_error` does — print the offending source line with a caret and the message — so
   out-of-tree consumers stop reimplementing it (§2.10).

---

## 1. Root cause / context

### 1.1 What is missing

A consumer holding a `SpanProtocol`-typed span has no way to get a `(line, column)` for error
reporting without reaching for raw `.start`/`.end`, no way to learn which file the span came from, and
no shared way to render a caret-annotated error line. Each of these forces a different out-of-tree
workaround.

The line/column lookup (`pos_to_line_col`) lives on `TerminalSource`, takes a raw integer position, and
is *not* part of any cross-backend protocol:

- Python: `TerminalSource.pos_to_line_col(pos: int) -> LineColPos` (`terminalsrc.py:183-205`).
- Rust: `TerminalSource::pos_to_line_col(pos: i64) -> Option<LineColPos>`
  (`crates/fltk-parser-core/src/terminalsrc.rs:180-228`) — Rust-internal, **not pyo3-exposed**.

`SpanProtocol` (`span_protocol.py:8-56`) deliberately omits `.start`/`.end` because their semantics
could differ between backends; it exposes only methods. There is no `line`, `column`, `line_col`, or
`pos_to_line_col` method on it, no `filename`, and no formatter.

### 1.2 Why it blocks the clockwork port

clockwork's `format_line_with_error` (`clockwork/dsl/ir/cst_util.py:70-92`) does:

```python
line_col = terminals.pos_to_line_col(span.start)          # reads span.start
return (
    f"\nIn {module_path}:{line_col.line + 1}:{line_col.col + 1}:\n"
    f"{get_span(line_col.line_span, terminals)}\n"        # needs the line text for the caret
    f"{' ' * line_col.col}^\n"                            # needs col
)
```

The `span` parameter is annotated as the concrete `terminalsrc.Span`, not `SpanProtocol`, *because* it
reads `span.start`. Migrating to `SpanProtocol` is blocked: `.start` is not on the protocol, and
`pos_to_line_col` is neither on the protocol nor pyo3-exposed on the Rust backend. clockwork needs three
things from one call: `line`, `col`, and the **line span** (the full text of the offending line). It
also threads a `terminals` argument purely to work around today's sourceless `line_span`
(`cst_util.py:46` "sourceless line_span residual"), and it carries a clockwork-specific `ModuleID` to
render the filename — there is no plain filename on the source.

clockwork also has a *second* formatter, the parse-error path (`parse.py:59-61`), which formats
`pos_to_line_col(error_position())` with no caret. Every other out-of-tree consumer that wants
caret-annotated errors must reinvent this same string assembly.

### 1.3 The mechanical reason both backends *can* satisfy this on the span

Both backends already carry the full source text inside the span:

- Python `Span._source: str | None` (`terminalsrc.py:54`) — the raw source string. `text()` resolves a
  slice from it (`terminalsrc.py:57-67`).
- Rust `Span.source: Option<Arc<SourceInner>>` (`span.rs:160`), `SourceInner.text: String`
  (`span.rs:47`). `text()` resolves a slice from it (`span.rs:286-327`).

So a `line_col()` method on the span can scan the carried source for `\n` and compute line/column —
exactly mirroring how `text()` already resolves through carried source. The `pos_to_line_col` bisect
logic needs only `(source text, position)`; both are present on the span. A `filename()` accessor needs
only a new optional field on the carried source (§2.8).

### 1.4 The one structural constraint that *shaped* the prior design — and how we now resolve it

**The `fltk._native` extension depends only on `fltk-cst-core`, not on `fltk-parser-core`** (workspace
edges confirmed in exploration-scope-expansion §A.1: `fltk-native → fltk-cst-core`;
`fltk-parser-core → fltk-cst-core`; `fltk-cst-core →` nothing). `Span`/`SourceInner` live in
`fltk-cst-core/src/span.rs`; `LineColPos` and `pos_to_line_col` live in
`fltk-parser-core/src/terminalsrc.rs` (`lib.rs:27` re-exports them). The pyo3 `Span` therefore cannot
*call* the existing Rust `pos_to_line_col`.

The prior draft concluded the logic must be **re-implemented** in `fltk-cst-core` and flagged the
duplication as a forced compromise. **Per user comment 1, we reject that.** The dependency direction
already runs `fltk-cst-core ← fltk-parser-core` and `fltk-cst-core ← fltk-native`:

```
fltk-cst-core   ←   fltk-parser-core
      ↑
  fltk-native
```

`fltk-cst-core` is the **lower** crate both consumers already depend on. So the clean single-location
fix is to **move `LineColPos` and the bisect logic down into `fltk-cst-core`** and have
`fltk-parser-core` re-export and call them (exploration §A.4 **Option 1**). This needs **no new Cargo
edge** (the `fltk-parser-core → fltk-cst-core` edge already exists at
`crates/fltk-parser-core/Cargo.toml:16`) and creates **no cycle**. One algorithm, one location, reached
by both crates and by the pyo3 `Span`. Detail in §2.5; the rejected alternatives (new dependency edge;
third crate) are in §7.

---

## 2. Proposed approach (API shape — this is the gate decision)

### 2.1 The protocol method

Add one method to `SpanProtocol`:

```python
def line_col(self) -> LineColPos | None: ...
```

- **Name:** `line_col`. Reads as "the line/column of this span." Matches `pos_to_line_col` without the
  `pos_` prefix (no integer argument; the span *is* the position).
- **Reported position:** the span's **start** only. This is exactly what clockwork consumes
  (`terminals.pos_to_line_col(span.start)`) and what the error formatter (§2.10) points the caret at.
  See §6 open question 1 on whether `end` is also wanted.
- **0- vs 1-based:** **0-based** line and column, matching `LineColPos` today on both backends
  (`terminalsrc.py:201-205`). clockwork has **two** consumption sites with different arithmetic: the
  human-readable header adds `+ 1` (`cst_util.py:89`), while the caret-indent line uses the raw 0-based
  `col` (`cst_util.py:91`, `' ' * line_col.col`). The caret is the strict 0-based consumer. Switching to
  1-based would silently shift every caret and break every existing `pos_to_line_col` consumer's `+ 1`
  arithmetic — a behavior change, not additive. We keep 0-based and document it loudly. The new error
  formatter (§2.10) owns the `+ 1` display convention so consumers don't re-derive it.
- **Tab handling:** columns count **codepoints**, not display columns. A tab is one codepoint = one
  column. Matches the existing `pos_to_line_col` (`terminalsrc.py:196,199`). No tab expansion.
- **End-of-input:** position `== len(source)` is clamped to `len - 1`, matching `pos_to_line_col`
  (`terminalsrc.py:187-188`, `terminalsrc.rs:185-186`). Position `> len` is out of domain.
- **Empty / zero-width spans:** a zero-width span `Span(p, p)` reports the line/col of `p`. A
  source-bearing span over empty source `""` with `start = 0` returns `LineColPos(line=0, col=-1, ...)`
  — the `col = -1` falls out of the end-of-input clamp (`start == len == 0` → `pos = -1`), a property of
  the inherited algorithm, not new behavior (see §3 empty-source note). A negative start (`start = -1`,
  the sentinel) returns `None` via a **new guard the span method applies before delegating** (next
  bullet).
- **Sourceless / out-of-domain spans (return `None`) — guard runs *before* the shared bisect:**
  `line_col()` returns `None` when the span cannot resolve a position, mirroring `text()`. These checks
  are a **new guard in the span-level wrapper**, evaluated *before* delegating to the shared
  `resolve_line_col` helper. This ordering is load-bearing: the shared helper inherits
  `pos_to_line_col`'s in-domain treatment of `pos = -1` and would itself return
  `LineColPos(line=0, col=-1)`, so the wrapper must short-circuit first. `None` is returned when:
  - no source is attached (`has_source()` is `False`): `UnknownSpan`, the default `Span(-1, -1)` on
    freshly-constructed CST node fields, or a consumer-built sourceless span;
  - `start < 0` (negative-index sentinels), even if a source were attached;
  - `start > len(source)` (out of domain).

### 2.2 The raising companion

For parity with `text()` / `text_or_raise()`, add:

```python
def line_col_or_raise(self) -> LineColPos: ...
```

Raises `ValueError` (same message family as `text_or_raise`: "has no source" / "has negative indices" /
"out of bounds for source of length N") instead of returning `None`. This is the natural form for the
error-reporting call site that *expects* a source-bearing span and wants a loud failure on a sentinel.
The error formatter (§2.10) calls this internally.

clockwork's `format_line_with_error` operates on parser-produced spans (always source-bearing), so its
migration to the fltk formatter (§2.10) keeps non-`Optional` control flow.

### 2.3 The filename accessor on the protocol

Add one method to `SpanProtocol`:

```python
def filename(self) -> str | None: ...
```

Returns the optional filename carried by the span's source (§2.8), or `None` when the source has no
filename or the span is sourceless. This lets the error formatter (§2.10) and any consumer learn a
span's file without threading a separate `filename` argument and without per-span storage. It is the
filename analogue of `text()`: read-through to the carried source, `None` when absent.

### 2.4 Return type: `LineColPos`

Return the existing `LineColPos` shape (`terminalsrc.py:155-159`):

```python
@dataclass(frozen=True, eq=True, slots=True)
class LineColPos:
    line: int
    col: int
    line_span: Span
```

Reasons to reuse it rather than a tuple or new type:

- It already carries `line_span`, which the formatter needs to render the caret line. A bare
  `(line, col)` tuple would drop it and force a separate `pos_to_line_col` call.
- It is the established return type of `pos_to_line_col` on both backends; reusing it means the span
  method and `TerminalSource.pos_to_line_col` return the *same shape*.
- `frozen/eq/slots` already match the protocol-surface conventions.

**`line_span` source-bearing-ness (equivalence detail):** today the Python `LineColPos.line_span` is
**sourceless** (`terminalsrc.py:197,200`), while the Rust one is **source-bearing** (`terminalsrc.rs:216,220`).
For the new span-level `line_col()`, **both backends produce a source-bearing `line_span`** (the span
already carries the source; passing it through costs nothing and is strictly more useful —
`line_span.text()` then works directly, which the formatter relies on). Span equality ignores source
(`span.rs:150-152`; Python `compare=False` on `_source`), so cross-backend `LineColPos` equality is
unaffected. This removes clockwork's `# sourceless line_span residual` workaround (`cst_util.py:46`) for
the span-method path. The legacy `TerminalSource.pos_to_line_col` Python path keeps its current
sourceless behavior, except that the sentinel for the final line is corrected from `len - 1` to
`len` on both backends (§2.5, bug-fix note).

**Return-type annotation precision:** `LineColPos.line_span` is typed as the concrete `terminalsrc.Span`.
On the Rust backend the field holds a Rust `Span`. This is the same cross-backend asymmetry already
accepted for `merge`/`intersect`. The protocol annotates the return as the Python `LineColPos | None`;
see §2.7 and §6 open question 3.

### 2.5 Single-location line/col logic — move `LineColPos` + bisect into `fltk-cst-core` (resolves comment 1)

This replaces the prior draft's "re-implement in `fltk-cst-core`, duplicate, flag as compromise"
approach. We **move** the owning code down one crate so there is exactly one copy.

**Target state (exploration §A.4 Option 1, §A.5):**

1. **`LineColPos` moves to `fltk-cst-core/src/span.rs`.** It is defined there as the canonical struct
   (`pub struct LineColPos { pub line: i64, pub col: i64, pub line_span: Span }`) and additionally made
   a **pyo3 pyclass** (§2.6) so the pyo3 `Span` can return it. `fltk-parser-core` deletes its own
   `LineColPos` definition (`terminalsrc.rs:18-23`) and re-exports the moved one: `terminalsrc.rs` adds
   `use fltk_cst_core::LineColPos;` and the crate-root re-export at
   `crates/fltk-parser-core/src/lib.rs:27` (`pub use terminalsrc::{LineColPos, TerminalSource};`) is
   **kept verbatim** — downstream `fltk_parser_core::LineColPos` users continue to resolve to the same
   (now moved) type. No downstream churn.

2. **The bisect becomes a shared free function in `fltk-cst-core/src/span.rs`:**

   ```rust
   pub fn resolve_line_col(text: &str, pos: i64, line_ends: &OnceLock<Vec<i64>>) -> Option<LineColPos>
   ```

   This is the *single* copy of the algorithm currently inlined at `terminalsrc.rs:191-227`. It takes
   the text, the (already domain-checked, already EOF-clamped) position, and a caller-owned
   `OnceLock<Vec<i64>>` line-ends cache, builds the cache on first use, bisects, and returns a
   source-bearing `LineColPos`. The `line_ends` cache is **passed in** rather than owned by the function
   so each caller controls cache lifetime (the parser caches on `TerminalSource`; the span caches on
   `SourceInner` — §2.8).

3. **`TerminalSource::pos_to_line_col` becomes a thin wrapper** (`terminalsrc.rs:180-228`): it keeps its
   public signature, its `pos > len` domain check, and the EOF clamp, then calls
   `fltk_cst_core::resolve_line_col(self.text(), pos, &self.line_ends)`. Its observable behavior is
   unchanged **except for one intentional bug fix**: the sentinel for the final line changes from
   `len - 1` to `len` (exclusive past-end) on both backends. The old `len - 1` sentinel caused the
   last character of a line to be absent from `line_span` when the source had no trailing `\n` —
   a latent bug. The fix is an undocumented behavioral change relative to the pre-implementation
   design text which said "unchanged," but is correct and required for parity with the new
   `Span.line_col()`. The inline Rust tests at `terminalsrc.rs:424-519` stay and still pass —
   they test the wrapper, which still exists.

4. **The pyo3 `Span::line_col` calls the same `resolve_line_col`** (§2.6), passing
   `&source_inner.line_ends` (the new cache on `SourceInner`, §2.8). One algorithm, three call sites
   (parser wrapper, pyo3 span, pure-Rust span helper), zero duplication.

**One behavior the move *fixes* (must be called out):** today the Python `pos_to_line_col` returns a
**sourceless** `line_span` while Rust returns a **source-bearing** one — a pre-existing cross-backend
asymmetry. The Rust move-down keeps Rust source-bearing (no change). On the **Python** side the new
`Span.line_col()` is source-bearing (§2.4); the legacy Python `TerminalSource.pos_to_line_col` is **not
touched** by the Rust move and keeps returning a sourceless `line_span`, so existing Python consumers of
that method see no change. We deliberately do **not** "fix" the legacy Python sourceless `line_span` in
this change (it would perturb consumers that rely on `Span` equality ignoring source but might observe
`line_span.text()` flipping from `None` to a value) — left as-is, noted, not a compromise forced by the
design but a scope boundary (§6 open question 3 touches the related typing question).

**Why this is genuinely possible (answering the user's "this should be possible somehow"):** the only
thing that made it look impossible in the prior draft was treating `pos_to_line_col`'s *home crate*
(`fltk-parser-core`) as fixed. It is not — `LineColPos` and the bisect have no dependency on anything in
`fltk-parser-core` (they need only `&str`, `i64`, and `Span`, all of which are in or below
`fltk-cst-core`). Moving them down is mechanical and dependency-direction-respecting. The duplication
flagged in the prior §7 **no longer exists**.

### 2.6 Rust backend implementation (`fltk-cst-core`)

With `LineColPos` and `resolve_line_col` now living in `fltk-cst-core/src/span.rs`:

1. **`LineColPos` becomes a pyo3 pyclass** (in addition to its plain-Rust use by `fltk-parser-core`).
   It is `#[cfg_attr(feature = "python", pyclass(frozen, eq))]` with getters `line: int`, `col: int`,
   `line_span: Span`. This is a *new pyo3-visible type* — additive, no existing symbol renamed. The
   plain-Rust `fltk-parser-core` usage is unaffected: a `#[pyclass]` struct is still an ordinary Rust
   struct when the `python` feature is off (and `fltk-parser-core` builds `fltk-cst-core` with
   `default-features = false`, so it never sees the pyo3 attributes — confirmed
   `crates/fltk-parser-core/Cargo.toml:16`).

   **Getter and equality specifics (resolves design-5):**
   - The `line_span` getter returns an **owned (cloned) `Span`**, not a borrow. A `frozen` pyclass
     cannot hand back a bare `&Span` field as a Python value; the getter clones (`Span` is
     `#[derive(Clone)]`, `span.rs:156`, so the clone is an O(1) `Arc` pointer bump — the source string
     is not copied). Write the getter as `#[getter] fn line_span(&self) -> Span { self.line_span.clone() }`
     (returning an owned `Span` that pyo3 wraps into a `Py<Span>`), not as a field-borrow getter.
   - `pyclass(eq)` requires `LineColPos: PartialEq`. The struct derives `PartialEq, Eq` today
     (`terminalsrc.rs:18`); the derive is coherent because its `line_span: Span` field's `PartialEq`
     ignores source (`span.rs:176-180`). The intended `LineColPos` equality is therefore **value-equal,
     source-ignoring** (two `LineColPos` with `line_span`s that differ only in attached source compare
     equal). This **matches** the Python `@dataclass(eq=True)` `LineColPos` (whose `line_span` equality
     also ignores source via the `compare=False` `_source` field) — the two backends' `LineColPos`
     equality agree, but only because *both* ignore source. Noted so the cross-backend `LineColPos`
     equality assertions (§4.1) are not surprised by it.

   **Registration path (required — the pyclass is otherwise not importable):**
   1. Export it from `fltk-cst-core/src/lib.rs:18` (today `pub use span::{SourceText, Span, SpanError};`)
      → add `LineColPos`.
   2. Re-export through the extension shim `src/span.rs:2` (today `pub use fltk_cst_core::{SourceText, Span};`)
      → add `LineColPos`.
   3. Bring it into scope in the extension crate root: `src/lib.rs:6` is
      `use span::{SourceText, Span};` → add `LineColPos` (or fully-qualify the `add_class` call). This
      import is the binding the `add_class` call in the next step resolves against; omitting it fails
      `cargo check` with an unresolved `LineColPos` name (design-4).
   4. Register with the module in `src/lib.rs:14-15` (today `m.add_class::<Span>()?;` /
      `m.add_class::<SourceText>()?;`) → add `m.add_class::<LineColPos>()?;`.

   Without all four, `from fltk._native import LineColPos` (and the pyi stub in §2.7) names an
   unreachable (or uncompilable) type.

2. **`Span::line_col_inner(&self) -> Option<LineColPos>`** (pure Rust, no pyo3) on `fltk-cst-core`'s
   `Span`: applies the **`start < 0` / sourceless / `start > len` guard first**, then EOF-clamps, then
   calls the shared `resolve_line_col(self.source_text(), start, &source_inner.line_ends)`. The
   `start < 0 → None` guard is a deliberate addition, not part of the shared bisect (which, like
   `pos_to_line_col`, treats `pos = -1` as in-domain and would return `LineColPos(line=0, col=-1)`). The
   pure-Rust unit tests (§4.3) pin this divergence: `Span(-1,-1).line_col() == None` while
   `pos_to_line_col(-1)` still returns `LineColPos(line=0, col=-1)`.

   **`Span.line_col()` deliberately diverges from legacy `pos_to_line_col` on *both* backends for
   negative positions — and the legacy domains themselves differ (resolves design-3).** The new
   `start < 0 → None` guard is uniform across backends, but the two legacy `pos_to_line_col`
   implementations it diverges *from* do **not** share a low-end domain:
   - Rust `pos_to_line_col` (`terminalsrc.rs:182`) rejects `pos < -1` (returns `None`) and treats
     `pos == -1` as in-domain (`LineColPos(line=0, col=-1)`).
   - Python `pos_to_line_col` (`terminalsrc.py:184`) has **no negative guard at all** — only `pos > len`
     raises. Any `pos < 0` (not just `-1`) flows into `bisect.bisect_left`; for `-1` it returns
     `LineColPos(line=0, col=-1)` (matching Rust at exactly `-1`), but for `pos < -1` it silently
     bisects a negative position rather than returning `None`.

   The move-down (§2.5) unifies only the **Rust** side; the **Python** legacy method is untouched
   (§2.5 final para). So for **any** negative `start`, the new `Span.line_col()` returns `None` while the
   legacy method returns a `LineColPos` — on Python for all `pos < 0`, on Rust for `pos < -1` (and at
   `pos == -1` both legacy methods return `LineColPos(line=0, col=-1)` while the span method still
   returns `None`). This is intentional: a sentinel/negative-index span is "no position," and `None` is
   the right answer. The drift anchor (§4.4) is therefore scoped to **non-negative source-bearing
   positions** on both backends, and the divergence is pinned by a deliberate test on each backend
   (§4.3), not left implicit.

3. **Line-ends cache on `SourceInner`:** add `line_ends: OnceLock<Vec<i64>>` to `SourceInner`
   (`span.rs:46-48`). The struct already anticipates this — its doc comment says the `Arc` indirection
   "leaves room for future cached metadata (e.g. line-offset tables)." Shared across all spans pointing
   to the same `Arc<SourceInner>`, so repeated `line_col()` calls on one parse pay the O(N) scan once,
   then O(log N_lines) per call (matching `TerminalSource`'s caching; exploration-codepoint-efficiency
   §3.3). `OnceLock<Vec<i64>>` is `Send + Sync`.

   **Shared-allocation nuance (acknowledged, accepted):** `SourceInner` is the same allocation
   `fltk-parser-core::TerminalSource` is built over, and `TerminalSource` *already* carries its own
   `line_ends: OnceLock<Vec<i64>>` (`terminalsrc.rs:46`). After this change there are two independently
   populated line-ends tables over the same immutable text — not a correctness risk (both derive
   deterministically from immutable `text`), but duplicated state. (A future consolidation could have
   `TerminalSource` read the `SourceInner` cache; out of scope. Note this consolidation is now
   *adjacent*, not blocked: with `resolve_line_col` shared, `TerminalSource::pos_to_line_col` could be
   pointed at `&self.source.inner.line_ends` instead of its own field — a small follow-up, captured as
   `TODO(linecol-cache-consolidate)` in §7.)

   **ABI impact:** changing `SourceInner`'s layout does **not** move the cross-cdylib ABI probe, which
   measures `size_of::<<SourceText as PyClassImpl>::Layout>()` (`span.rs:108-138`, `lib.rs:57-75`).
   `SourceText` holds only `Arc<SourceInner>` (one pointer) regardless of `SourceInner`'s contents
   (`span.rs:56-58`), so the probe value is **unchanged**; no ABI-marker bump.

4. **pyo3 wrappers under `#[pymethods] impl Span`** (`span.rs:382-604`):
   - `#[pyo3(name = "line_col")] fn py_line_col(&self, py) -> PyResult<Option<Py<LineColPos>>>` —
     constructs the pyclass from `line_col_inner()`, or `None`.
   - `fn line_col_or_raise(&self, py) -> PyResult<Py<LineColPos>>` — raises `PyValueError` (message
     family matching `text_or_raise`, `span.rs:480-517`).
   - `#[pyo3(name = "filename")] fn py_filename(&self) -> Option<String>` — returns
     `self.source.as_ref().and_then(|s| s.filename.clone())` (§2.8). `None` when sourceless or
     filename-less.

   All follow the existing `py_text` pattern: inner Rust method does the work, pyo3 wrapper converts the
   return type.

5. **Byte-vs-codepoint:** line/column counting uses **codepoint** indices directly — the same units
   `Span.start` is stored in (`span.rs:140-148`). No byte translation needed (unlike `text()`). The
   line-ends table stores codepoint indices of `\n` (built via `text.chars().enumerate()`,
   `terminalsrc.rs:195-200`, **not** `char_indices()`). This guarantees Python (which indexes by
   codepoint natively) and Rust return **identical** `(line, col)`. Confirmed against
   exploration-codepoint-efficiency §1-2.

### 2.7 The pyi stub (`fltk/_native/__init__.pyi`)

Additive edits:

- Add `class LineColPos:` with `line: int`, `col: int`, `line_span: Span` (read-only properties).
- Add to `class Span:`:
  ```python
  def line_col(self) -> LineColPos | None: ...
  def line_col_or_raise(self) -> LineColPos: ...
  def filename(self) -> str | None: ...
  ```
- Add `filename: str | None = None` to `SourceText.__init__` (§2.8):
  ```python
  def __init__(self, text: str, filename: str | None = None) -> None: ...
  ```

A subtlety: the Python backend's `LineColPos` lives in `fltk.fegen.pyrt.terminalsrc`, the Rust backend
returns `fltk._native.LineColPos`. Two distinct classes (just as Python/Rust `Span` are). The protocol
return type names the Python class as canonical; consumers access `.line/.col/.line_span` on either. See
§6 open question 3.

### 2.8 Optional filename — stored once on the source allocation (resolves comment 2a)

Filename is caller-provided at source construction, stored **once** on the source allocation, never
per-span, optional end-to-end. Construction/threading sites (exploration §B):

**Rust core (`fltk-cst-core/src/span.rs`, `fltk-parser-core/src/terminalsrc.rs`):**

| Site | File:line | Change |
|------|-----------|--------|
| `SourceInner` | `span.rs:46-48` | Add `pub(crate) filename: Option<String>` |
| `SourceText::from_str` | `span.rs:65` | Add `filename: Option<&str>` param; set on `SourceInner` |
| `SourceText::new` (pyo3 `#[new]`) | `span.rs:88` | Add `filename: Option<&str>` with `#[pyo3(signature = (text, filename=None))]` default |
| `TerminalSource::new` | `terminalsrc.rs:51` | Add `filename: Option<&str>`; pass to `SourceText::from_str` |
| `TerminalSource::from_source_text` | `terminalsrc.rs:56` | No new param — `SourceText` already carries filename |

`Span.filename()` reaches the stored value via
`self.source.as_ref().and_then(|s| s.filename.as_deref())`.

Every existing Rust caller of `SourceText::from_str(text)` must add a `None` argument
(`SourceText::from_str(text, None)`). These are in-tree call sites (the parser-core constructor,
fixtures, tests); they are not the public Python API. The public Python `SourceText(text)` call keeps
working because the pyo3 `#[new]` gives `filename` a `None` default.

**Rust *parser* path — filename must reach the real parse, not just the hand-built `SourceText`
(resolves design-1).** The prior revision claimed the "Rust-backend caller entry point for filename is
the pyo3 `SourceText` constructor." That is wrong for **parser-produced** spans. On the Rust backend the
generated pyo3 parser ctor takes a raw `str`, builds the `SourceText` *itself*, and never accepts a
caller-built `SourceText`:

- `crates/fegen-rust/src/parser.rs:1399-1407` — `PyParser::new(text: &str, capture_trivia, max_depth)`
  → `Parser::new(text, …)`.
- `crates/fegen-rust/src/parser.rs:57-59` — `Parser::new(text)` →
  `Self::from_source_text(SourceText::from_str(text), …)`.
- clockwork's Rust path confirms it: `_RustParseBackend.parse` calls `self._rparser_mod.Parser(source)`
  with a plain string (`~/tps/clockwork/clockwork/dsl/ir/parser_backend.py:145`); there is no
  `Parser.from_source_text` pyo3 entry — `register_classes` adds only `PyParser`/`PyApplyResult`
  (`parser.rs:1649-1651`).

So a `filename` on the pyo3 `SourceText` ctor does **nothing** for a Rust *parse*; the ctor is not on
that path. `crates/fegen-rust/src/parser.rs` is **generated** (its header reads "Generated by fltk
gen-rust-parser … Do not edit"); the emitter is **`fltk/fegen/gsm2parser_rs.py`** (the Rust-parser
generator — distinct from `gsm2parser.py`, which emits the *Python* parser). To put a filename on a
Rust-parser span we thread `filename` through the generated Rust parser ctors and **regen the Rust
parser** (parallel to the Python regen, §4.6/§5/§7):

| Site | File:line | Change |
|------|-----------|--------|
| `Parser::new` (emitted) | `gsm2parser_rs.py:380-381` | Emit `pub fn new(text: &str, filename: Option<&str>, capture_trivia: bool)` → `Self::from_source_text(SourceText::from_str(text, filename), …)` |
| `Parser::from_source_text` (emitted) | `gsm2parser_rs.py:384-385` | No new param — `SourceText` carries filename |
| `PyParser::new` (emitted pyo3 `#[new]`) | `gsm2parser_rs.py:944-947` | Emit `#[pyo3(signature = (text, filename = None, capture_trivia = false, max_depth = None))]` and pass `filename` to `Parser::new` |
| Regenerated output | `crates/fegen-rust/src/parser.rs:57-59,1399-1407` | The above land here after regen |

This makes the **Rust caller entry point for parser filename** the pyo3 `Parser` constructor —
`Parser(source, filename="f.clk")` — mirroring the Python path (where filename is supplied on
`TerminalSource` and the generated Python parser forwards it into `SourceText`). The pyo3 `SourceText`
ctor filename remains useful for the **hand-built** `SourceText` path (a consumer constructing a span
directly), but it is **not** the parser path. Both `filename` params keep a `None` default, so
`Parser(source)` / `SourceText(text)` are unchanged.

**Cross-cutting consumer note (clockwork):** clockwork's Rust backend currently calls `Parser(source)`
with no filename (`parser_backend.py:145`); to get filenames on Rust-parse spans it would pass
`Parser(source, filename=...)`. This is an additive, opt-in call-site change on the consumer, not a
forced break — `Parser(source)` keeps working and yields `filename() == None`.

**Python (`fltk/fegen/pyrt/terminalsrc.py`):**

| Site | File:line | Change |
|------|-----------|--------|
| `SourceText` dataclass field | `terminalsrc.py:9-21` | Add `_filename: str \| None` field |
| `SourceText.__init__` | `terminalsrc.py:20` | Add `filename: str \| None = None`; `object.__setattr__(self, "_filename", filename)` |
| `TerminalSource.__init__` | `terminalsrc.py:163` | Add `filename: str \| None = None`; store `self.filename: Final = filename` |
| `Span.filename()` | new on `Span` | Return `self._source_filename` (see threading note) |

**Threading filename onto the Python `Span`.** The Python `Span` stores `_source: str | None` (a raw
`str`, *not* a `SourceText`); `with_source` unwraps `SourceText._text` into that raw `str`
(`terminalsrc.py:142-149`). To let a Python `Span` report its filename without changing the equality/
hash surface, add a second sentinel-default field `_source_filename: str | None = field(default=None,
compare=False, hash=False, repr=False)`, populated by `with_source` from `SourceText._filename` (or left
`None` when a bare `str` source is passed). `Span.filename()` returns `_source_filename`. This is
additive: `compare=False, hash=False` means it does **not** perturb `Span` equality or hashing (which
already exclude `_source`), so all existing `Span` equality/identity behavior and tests are unchanged.

**Generated parser threading (Python).** The generated `Parser.__init__` builds `_source_text` from
`terminalsrc.terminals` (`fltk_parser.py:16`; IIR at `gsm2parser.py:105-118`). To carry filename
through, the IIR `_source_text` init expression gains a second kwarg reading
`terminalsrc.filename`, so the generated line becomes
`SourceText(text=terminalsrc.terminals, filename=terminalsrc.filename)`. This requires a **regen** of
the Python parsers (and `make fix`), because the construction expression in `gsm2parser.py:107-118`
changes. The change is additive at runtime — a `TerminalSource` constructed without a filename yields
`filename=None`, and `SourceText(text=..., filename=None)` is identical in behavior to today's
`SourceText(text=...)`. (Contrast: the prior draft asserted "no regen needed." That held when filename
was out of scope; **with** filename threading through the generated parser constructor, regen *is*
required. The full regen scope — both backends — is in §4.6 and §5.)

**Optionality end-to-end (the user's hard requirement).** No code branches on filename — it is stored
and retrieved, never interpreted by the runtime. `TerminalSource("src")` /
`TerminalSource("src", filename="f.clk")` both work; `SourceText("src")` / `SourceText("src", "f.clk")`
both work; a span over filename-less source returns `filename() == None`. Dynamic snippets with no file
parse exactly as today.

**Atomicity: the Python regen and the Rust `SourceText::new` filename param must land together
(resolves design-9).** The generated Python parser's `_source_text` line uses
`fltk.fegen.pyrt.span.SourceText` — the **backend selector** (`fltk/fegen/pyrt/span.py:10-13`), which
resolves to the **Rust** pyo3 `SourceText` whenever `fltk._native` is importable. So the regenerated
`SourceText(text=…, filename=…)` calls the *Rust* `SourceText.__new__` with a `filename` kwarg at
runtime. If the Python regen merges **before** the Rust `SourceText::new` gains its `filename=None`
param, every run of a generated Python parser under the Rust span backend raises
`TypeError: unexpected keyword argument 'filename'`. These two changes are **not independently
mergeable** — they must land in the same change. (Symmetrically: the Rust *parser* generator change in
the §2.8 Rust-parser path and the Rust `Parser::new`/`from_source_text`/`SourceText::from_str` param
changes are emitted together by `gsm2parser_rs.py`, so they regen as one unit.) Called out in §5.

### 2.9 Filename equivalence across backends

The two backends differ in *where* the caller supplies the filename, but each backend now has a real
**parser** entry point for it, so the cross-backend equivalence test exercises actual parses (not just
hand-built sources):

- **Python:** filename is supplied on `TerminalSource(text, filename=...)`; the generated Python parser
  forwards it into `SourceText` (§2.8 Python table).
- **Rust:** filename is supplied on the generated pyo3 parser ctor `Parser(source, filename=...)`, which
  threads it into `Parser::new` → `SourceText::from_str` (§2.8 Rust *parser* path).

Both **agree on the observable result**: `span.filename()` returns the same `str | None` for the same
logical source. The cross-backend equivalence tests (§4.1) assert this directly by **parsing** on each
backend with a filename set and asserting `span.filename()` matches — implementable because §2.8 now
threads filename to a real parse on both backends. (The hand-built `SourceText(text, filename)` path is
additionally covered as a separate case, but it is no longer the *only* Rust path.)

### 2.10 The shared error formatter (resolves comment 2b)

Add one fltk public function that does what clockwork's `format_line_with_error` does — render the
offending source line with a caret and the message — minus the clockwork-specific `ModuleID`
path-rendering (which stays in clockwork).

**Placement:** a new module `fltk/fegen/pyrt/error_formatter.py`. (Not `pyrt/errors.py` — that already
exists and is the parser's `ErrorTracker`/`ParseContext` machinery, `errors.py:1-152`; overloading it
would muddy two unrelated concerns. A dedicated module is the clean public home, importable as
`from fltk.fegen.pyrt.error_formatter import format_source_line`.)

**Signature:**

```python
def format_source_line(
    span: SpanProtocol,
    message: str,
    *,
    filename: str | None = None,
) -> str: ...
```

- `span: SpanProtocol` — backend-agnostic. The function calls `span.line_col_or_raise()` (parser spans
  are always source-bearing; a sentinel raises loudly, which is correct for an error path) and
  `lc.line_span.text() or ""` (source-bearing after §2.4). It does **not** read `.start`/`.end`, so it
  works for both backends and unblocks the clockwork annotation migration.
- `message: str` — the error message body.
- `filename: str | None` (keyword-only, default `None`) — explicit override. When omitted, the function
  falls back to `span.filename()` (§2.3). Precedence: an explicit `filename` argument wins over
  `span.filename()` (lets callers like clockwork pass a rendered `ModuleID` path while still benefiting
  from the rest). When both are `None`, the header omits the file (see output).

**Output** (string, trailing newline, mirroring clockwork's shape but with the message appended):

```
\nIn <file>:<line+1>:<col+1>:\n<line text>\n<col spaces>^\n<message>\n
```

When no filename is resolvable, the header degrades to `At line <line+1>, column <col+1>:` (no `In
<file>` prefix). Line and column are rendered **1-based** in the header (`lc.line + 1`, `lc.col + 1`),
the caret indent uses the raw **0-based** `lc.col` (`' ' * lc.col`) — preserving clockwork's exact two
conventions (`cst_util.py:89-91`) so migrated output is byte-identical apart from the now-appended
message and the file-rendering difference clockwork supplies via the `filename` argument. The
empty-source `col = -1` corner (§3) is harmless here: Python's `' ' * -1 == ''`, so the caret lands at
column 0 with no special-casing — the formatter does not need a `max(col, 0)` clamp.

**What clockwork keeps and what it drops on migration:**

- Drops its hand-rolled caret assembly and the `get_span(..., terminals)` sourceless fallback (the
  `terminals` argument disappears — `line_span` is source-bearing now).
- Keeps its `ModuleID` → path rendering, passing the result as
  `format_source_line(span, msg, filename=str(module_id.get_base_path()) if module_id and module_id.name
  else None)`.
- Migrates the `span` annotation from `terminalsrc.Span` to `SpanProtocol`.

**Backend-agnostic, no clockwork types.** The formatter imports only `SpanProtocol` from fltk; no
`ModuleID`, no `TerminalSource`. Any out-of-tree consumer calls it directly. (It deliberately does
**not** subsume clockwork's caret-less parse-error path at `parse.py:59-61`, which formats a raw
`error_position()` integer, not a span — see §6 open question 4.)

### 2.11 The protocol return-type annotations

`SpanProtocol.line_col` / `.filename` need concrete return annotations:

- `line_col` → **`terminalsrc.LineColPos | None`** (chosen). The Rust `LineColPos` is structurally
  identical and only ever obtained *from* a Rust span, so a consumer typing `x: SpanProtocol` gets
  `.line/.col/.line_span` regardless of backend. Names the Python class as canonical, exactly as
  `merge`/`intersect` annotate `SpanProtocol` while concretely returning a backend `Span`. No annotation
  churn for consumers.
- `filename` → `str | None`. Trivial, identical on both backends.
- (alternative, deferred) `AnyLineColPos = PyLineColPos | RustLineColPos` / `LineColPosProtocol`,
  paralleling `AnySpan`. Heavier; only needed if a consumer must `isinstance`-check the result across
  backends. Deferred to §6 open question 3.

### 2.12 What does NOT change

- No existing public symbol renamed; no existing method signature changed; `.start`/`.end` stay off the
  protocol. The change is additive: three protocol methods (`line_col`, `line_col_or_raise`,
  `filename`), the matching span methods on both backends, the moved-and-pyo3'd `LineColPos`, the
  optional `filename` constructor params, and one new formatter function.
- `fltk.fegen.pyrt.terminalsrc.LineColPos` already existed and is reused unchanged (Python backend).
  The *Rust* `LineColPos` moves crates (`fltk-parser-core` → `fltk-cst-core`) but keeps its
  `fltk_parser_core::LineColPos` re-export name (§2.5), so no downstream Rust consumer is affected.
- **Regen is required for BOTH parser backends** (§2.8): the Python generated parsers because the
  `_source_text` construction expression threads `filename`, **and** the Rust generated parsers because
  the emitted `Parser::new` / `PyParser::new` ctors thread `filename` onto the real parse path (the
  Rust-parser path the prior revision missed — design-1). This is a departure from the prior draft's "no
  regen." In-tree Rust call sites of `SourceText::from_str` additionally add a `None` argument (§2.8).

---

## 3. Edge cases / failure modes

| Case | Input | `line_col()` | `line_col_or_raise()` | `filename()` |
|------|-------|--------------|------------------------|--------------|
| Parser-produced span, file set | source-bearing, `start ∈ [0, len]`, filename present | `LineColPos(...)` | `LineColPos(...)` | `"f.clk"` |
| Parser-produced span, no file | source-bearing, filename `None` | `LineColPos(...)` | `LineColPos(...)` | `None` |
| `UnknownSpan` / `Span(-1,-1)` | no source, `start = -1` | `None` (wrapper guard) | `ValueError` ("no source") | `None` |
| Consumer sourceless span | no source, `start = 5` | `None` | `ValueError` ("no source") | `None` |
| Negative start, source attached | `start = -1` | `None` | `ValueError` ("negative indices") | filename of source |
| `start == len(source)` (EOF) | source-bearing | line/col of last char (clamped) | same | filename |
| `start > len(source)` | source-bearing | `None` | `ValueError` ("out of bounds") | filename |
| Zero-width span `Span(p,p)` | source-bearing | line/col of `p` | same | filename |
| Empty source `""`, `start = 0` | source-bearing, `len = 0` | `LineColPos(line=0, col=-1, line_span=Span(0,-1))` | same | filename |
| Multibyte source (Rust) | `é` etc. | codepoint column, identical to Python | same | filename |
| Tab in line | `\t` before start | counts as 1 column | same | filename |

**Empty-source note:** with `source = ""`, `len = 0`, `start = 0`: the EOF clamp fires
(`start == len → pos = -1`) and the bisect yields `line = 0, col = -1`. The clamp (not a sentinel start)
is the source of the `-1`; the `start = -1` sentinel rows are instead short-circuited to `None` by the
wrapper *before* any clamp. This `col = -1` corner is a property of the *existing* algorithm we are
sharing (not duplicating, now), pinned cross-backend by `pos_to_line_col_empty_input`
(`terminalsrc.rs:496-502`). Flagged in §6 if the user wants different empty-source semantics.

**Failure modes guarded:**

- **Backend divergence on multibyte input** — the single most important failure mode. Mitigated by
  counting codepoints on *both* backends (§2.6.5), the *shared* algorithm (one copy, §2.5), and an
  explicit equivalence test on multibyte sources (§4.1).
- **Backend divergence on filename** — mitigated by the filename being a stored-and-retrieved opaque
  string with no interpretation, and a direct cross-backend equivalence assertion (§4.1).
- **`line_ends` cache staleness** — `SourceInner`/`text` is immutable after construction; `OnceLock`
  initializes once; no staleness.
- **Protocol `isinstance` breakage** — adding methods to a `@runtime_checkable Protocol` makes
  `isinstance(x, SpanProtocol)` return `False` for any class implementing only the old set. Both in-tree
  backends are updated together. Out-of-tree consumers with hand-written `SpanProtocol` stubs must add
  `line_col` / `line_col_or_raise` / `filename` — inherent to extending a runtime-checkable protocol
  (same as when `merge`/`intersect` were added). Called out in §5.
- **Formatter on a sentinel span** — `format_source_line` calls `line_col_or_raise()`, so a sentinel
  raises `ValueError` rather than emitting a garbage caret. Correct for an error path; documented.

---

## 4. Test plan (TDD — tests written first, must fail, then implement)

Following the codebase TDD protocol. Tests land before implementation.

### 4.1 Cross-backend equivalence (the spec-level tests) — `tests/test_span_protocol.py`

New `TestLineColCrossBackend` + `TestFilenameCrossBackend`, parameterized over both backends (Python
`Span`, Rust `Span` via the existing `_rust_available` skip pattern). For each backend, build a span
with `with_source` over a shared `SourceText`/str (with and without a filename) and assert:

- **line/col:** `line_col()` / `line_col_or_raise()` return **bit-identical** `(line, col)` and an equal
  `line_span`. Cases: multi-line ASCII (line 0, line 1, line start, mid-line); multibyte
  (`"café\nrésumé"`, start after `é` — codepoint columns match); tab before start (counts 1); EOF
  (`start == len`); zero-width; `line_span.text()` returns the full offending line on both backends;
  sourceless span and `UnknownSpan` → `None` / `ValueError`; out-of-domain (`start > len`) →
  `None` / `ValueError`.
- **filename:** a span built over a source **with** a filename returns that filename on both backends; a
  span over a source **without** a filename returns `None` on both backends; a sourceless span returns
  `None`. The with/without-filename pair directly exercises optionality (comment 2a's hard requirement).
  The **parser path is the load-bearing case** (design-1): the with-filename case must use a real
  **parse** on each backend — Python via `TerminalSource(text, filename=...)` → `Parser`, Rust via the
  generated pyo3 `Parser(source, filename=...)` (§2.8) — and assert the parser-produced span reports the
  filename. A hand-built `SourceText(text, filename)` case is retained additionally, but on its own it
  would not prove the headline "a parser-produced span can tell you its file" on the Rust backend. This
  test is the regression guard that the Rust-parser generator change (§2.8) actually landed.

A helper iterates `[PySpan, RustSpan]` and asserts field-by-field agreement on every case (the
cross-backend equality assertion is the load-bearing one).

### 4.2 Protocol conformance — `tests/test_span_protocol.py`

- Extend `TestProtocolConformance*`: a span still `isinstance(s, SpanProtocol)` after adding the three
  methods (both backends).
- Extend `TestProtocolHasNoStartEnd`: assert `callable(SpanProtocol.line_col)`,
  `callable(SpanProtocol.line_col_or_raise)`, `callable(SpanProtocol.filename)`; `.start`/`.end` still
  absent.

### 4.3 Per-backend behavior

- `tests/test_span.py` (Python): `line_col` / `line_col_or_raise` / `filename` on `terminalsrc.Span` —
  sourceless `None`/raise, normal positions, EOF clamp, source-bearing `line_span` (`line_span.text()`
  works), filename present/absent, parity with `TerminalSource.pos_to_line_col` on the same
  `(source, start)` **for non-negative positions only**. Plus: `Span` equality/hash **unchanged** by the
  new `_source_filename` field (two spans with same `(start, end)` but different filenames still compare
  equal — pins `compare=False`). **Plus a deliberate Python negative-position divergence test
  (mirroring the Rust one): a source-bearing `Span(-1, ...)` returns `line_col() == None` while
  `TerminalSource(src).pos_to_line_col(-1)` returns `LineColPos(line=0, col=-1)` — pinning that the new
  guard intentionally diverges from the unguarded legacy Python method (design-3), so the divergence is
  not mistaken for an implementation bug during TDD.**
- `tests/test_rust_span.py` (Rust): new `TestLineCol` + `TestFilename` mirroring the above against
  `fltk._native.Span`; plus a multibyte case and a `LineColPos` field-access test.
- `crates/fltk-cst-core/src/lib.rs` / `span.rs` `#[cfg(test)]`: pure-Rust unit tests for `resolve_line_col`
  and `Span::line_col_inner` paralleling the existing `pos_to_line_col` tests (first line, second line,
  last line, EOF clamp, empty input, multibyte column, out-of-domain `None`). **Plus a
  deliberate-divergence test for the `start < 0` guard:** assert `Span(-1,-1).line_col() == None` while
  `TerminalSource::pos_to_line_col(-1)` still returns `LineColPos(line=0, col=-1)` — pinning the
  span-method's intentional divergence so a future refactor can't drop the guard.
- `crates/fltk-parser-core/src/terminalsrc.rs` `#[cfg(test)]` (existing, `terminalsrc.rs:424-519`):
  unchanged — they now exercise the thin wrapper over the **shared** `resolve_line_col`, proving the
  move-down preserved `TerminalSource::pos_to_line_col` behavior exactly.

### 4.4 Shared-helper / drift anchor

Because the algorithm is now a **single shared function** (`resolve_line_col`), the prior draft's
"two copies can't drift" anchor is mostly obviated — there is one copy. Retain a regression assertion
(in `tests/test_span_protocol.py` or `tests/test_span.py`) that `span.line_col()` and
`TerminalSource(src).pos_to_line_col(span.start)` agree for a source-bearing span **at non-negative
positions**, pinning that the **Python** span path and the Python `TerminalSource` path stay equivalent
(these remain two implementations on the Python side; Rust is now genuinely one). The anchor is
deliberately scoped to non-negative positions because the span method's `start < 0 → None` guard
diverges from the unguarded Python legacy method below zero (§2.6.2, design-3) — that divergence is its
own dedicated test (§4.3), not a drift-anchor case.

### 4.5 Error-formatter tests — `tests/test_error_formatter.py` (new)

- **Output shape:** `format_source_line(span, "boom", filename="f.clk")` produces the exact expected
  string (header `In f.clk:<line+1>:<col+1>:`, the offending line text, the caret at `' ' * col`, then
  `boom`). Assert the full multi-line string literally.
- **Filename precedence:** explicit `filename=` wins over `span.filename()`; with neither, the header
  degrades to `At line .../column ...:` with no `In <file>`; with only `span.filename()`, the header
  uses it.
- **Multibyte caret alignment:** a span after a multibyte char puts the caret at the correct codepoint
  column on both backends.
- **Cross-backend:** the same logical span/source on Python and Rust backends produces the **same**
  formatter output (the load-bearing equivalence for the consumer-facing function). Because the `In
  <file>:` header reads `span.filename()`, the cross-backend case must **parse** on both backends with a
  filename set (§2.8 threads it to a real parse on each), so both headers render `In <file>:` rather
  than one degrading to `At line …` — design-1's resolution is what makes this case match. A separate
  case exercises the `span.filename()` fallback explicitly to pin the parser-filename path on each
  backend.
- **Sentinel span:** `format_source_line(UnknownSpan, "x")` raises `ValueError` (via
  `line_col_or_raise`).

### 4.6 Regen / build / gate flow

- `span_protocol.py`, `terminalsrc.py`, `error_formatter.py`, `span.rs`, `terminalsrc.rs`, the pyi
  stub, and the `lib.rs`/`span.rs` Rust tests are hand-written.
- **Regen IS required for BOTH parser backends:**
  - **Python parsers** (`gsm2parser.py` `_source_text` init changes to thread `filename`): run the
    generator, then `make fix`, then commit — the project's standard regen → fix → commit flow
    (CLAUDE.md "Generated Code and Formatting").
  - **Rust parsers** (`gsm2parser_rs.py` `Parser::new` / `PyParser::new` emission changes to thread
    `filename`, §2.8 Rust-parser path): regen the Rust parser (`crates/fegen-rust/src/parser.rs` and any
    other generated Rust parsers), `cargo fmt`, then `uv run --group dev maturin develop` so Python
    tests see the new `Parser(source, filename=...)` signature. Without this regen the §4.1/§4.5
    cross-backend filename cases cannot pass on the Rust backend (design-1).
  Both are a departure from the prior draft (which predated filename scope and asserted "no regen").
- Rust changes require `uv run --group dev maturin develop` before Python tests see the new methods.
- `make check` is the precommit gate: ruff check + format-check + pyright + pytest + cargo check +
  clippy + cargo test. The new pyclass/methods and the moved `LineColPos`/`resolve_line_col` must pass
  clippy.

After the change, the suite contains: cross-backend `line_col` + `filename` equivalence tests; error-
formatter tests (shape, precedence, multibyte, cross-backend, sentinel); per-backend `line_col` /
`filename` tests; Rust unit tests for `resolve_line_col` / `line_col_inner`; the unchanged
`TerminalSource::pos_to_line_col` wrapper tests (proving the move-down); protocol-conformance assertions
for the three new methods; and the Python drift-anchor.

---

## 5. Public-API / compatibility summary

- **Additive only at the Python public surface.** No generated public symbol renamed; no existing method
  signature changed; `.start`/`.end` remain off the protocol; no consumer annotation churn for callers
  typing `SpanProtocol`. The `SourceText`/`TerminalSource` constructor gains an **optional** `filename`
  with a `None` default — existing `SourceText(text)` / `TerminalSource(text)` calls are unchanged.
- **New public surface:** `SpanProtocol.line_col` / `.line_col_or_raise` / `.filename`; the matching
  `Span` methods on both backends; `fltk._native.LineColPos` pyclass; the `filename` constructor params;
  `fltk.fegen.pyrt.error_formatter.format_source_line`; pyi stub additions.
  `fltk.fegen.pyrt.terminalsrc.LineColPos` is reused unchanged.
- **Rust internal move (not a public break):** the Rust `LineColPos` moves from `fltk-parser-core` to
  `fltk-cst-core`, re-exported from `fltk_parser_core::LineColPos` so downstream Rust consumers are
  unaffected. In-tree Rust callers of `SourceText::from_str` add a `None` filename argument.
- **Regen required for BOTH parser backends** (correcting the prior "Python parsers only"): the Python
  parser generator (`gsm2parser.py`) threads `filename` into the `_source_text` construction, **and** the
  Rust parser generator (`gsm2parser_rs.py`) threads `filename` into the emitted `Parser::new` /
  `PyParser::new` so Rust *parser*-produced spans can carry a filename (§2.8 Rust-parser path,
  design-1). Both regenerated outputs are behaviorally identical when no filename is supplied. The
  Rust-parser regen is the change that makes the cross-backend filename feature/test (§2.9/§4.1)
  implementable on the Rust backend.
- **Atomic landing (design-9):** the Python regen and the Rust `SourceText::new` `filename` param must
  ship together — the generated Python parser's `SourceText(text=…, filename=…)` resolves to the Rust
  pyo3 `SourceText` under the Rust backend (`span.py:10-13`), so a Python regen merged ahead of the Rust
  ctor param raises `TypeError` at runtime (§2.8).
- **Runtime-checkable protocol extension:** out-of-tree consumers with hand-written `SpanProtocol` stubs
  must add the three methods (same property that applied when `merge`/`intersect` were added).
- **`line_span` improvement:** the span-method path returns a *source-bearing* `line_span` on both
  backends, letting clockwork drop its `get_span(..., terminals)` sourceless fallback on that path. The
  legacy `TerminalSource.pos_to_line_col` Python behavior is left untouched **except for the sentinel
  bug fix** (see §2.5, note 3): `line_span.end` for the final line of a source without a trailing
  `\n` is now `len` (inclusive of last character) rather than `len - 1` (which truncated it). This is
  a behavioral change to the legacy method, intentional and correct.

---

## 6. Open questions (user judgment)

1. **`start`-only vs also reporting `end`.** The proposal reports the span's start line/col only (all
   current consumers, including clockwork and the new formatter, want exactly that). The error formatter
   (§2.10) cements start-only: it points one caret at the start. If you want the end too (e.g.
   multi-line span underlining) it would add `end_line_col()` / change the return shape. **Default:
   start only.** *(Status: still genuinely open; the formatter design makes start-only the natural
   choice but does not foreclose adding `end` later additively.)*

2. **Empty-source `col = -1` corner.** With empty source and `start = 0`, the shared algorithm yields
   `line=0, col=-1` (both backends agree). The proposal preserves this in `LineColPos` for cross-backend
   parity rather than cosmetically forcing `col=0` (which would diverge the span method from
   `TerminalSource.pos_to_line_col`). The formatter renders this harmlessly (caret at column 0, §2.10),
   so the only question is whether `LineColPos.col` itself should read `-1` or `0` for empty source.
   **Default: preserve `-1`** (matches the existing algorithm; low stakes).

3. **`LineColPos` cross-backend type handling + legacy Python sourceless `line_span`.** The proposal
   annotates the protocol return as `terminalsrc.LineColPos | None` and lets the Rust backend return a
   structurally-identical `fltk._native.LineColPos` (parallel to Python/Rust `Span`). If you want a
   first-class `AnyLineColPos` union and/or `LineColPosProtocol` (for cross-backend `isinstance`), that
   is a larger additive surface — flag it and it goes in. Relatedly, the legacy Python
   `TerminalSource.pos_to_line_col` keeps its **sourceless** `line_span` (the new `Span.line_col()` is
   source-bearing); we left the legacy path alone to avoid perturbing its consumers. Confirm that scope
   boundary, or ask to also make the legacy Python `line_span` source-bearing for full parity.
   **Default: single-annotation form, no `AnyLineColPos`; legacy Python path untouched.** (Confirmed: no
   consumer imports `LineColPos` directly — clockwork accesses it only via field access on a return
   value.)

4. **Formatter scope: caret path only, or also the caret-less parse-error path?** `format_source_line`
   covers the span-based, caret-annotated error (clockwork's `format_line_with_error`). clockwork also
   has a caret-less parse-failure formatter that works from a raw `error_position()` integer, not a span
   (`parse.py:59-61`). The proposal does **not** subsume it (it has no span). If you want fltk to also
   own that path, it would need a second helper taking `(terminals, pos, message)` or accepting a raw
   position. **Default: ship only the span-based caret formatter now.** *(Status: genuinely open —
   small additional surface if wanted.)*

5. **`line_col_or_raise` necessity.** The proposal ships both the `None`-returning and raising forms,
   mirroring `text()` / `text_or_raise()`. The formatter uses the raising form. If you'd rather ship only
   `line_col() -> LineColPos | None`, that halves the surface but forces the formatter (and clockwork) to
   handle `None` explicitly. **Default: ship both** — clockwork's control flow is non-`Optional` and a
   parser span is always source-bearing.

*(Resolved by this revision, no longer open: the line/col **duplication** question — comment 1 — is
settled by the move-down in §2.5, §7; the **filename storage location** — comment 2a — is settled as
once-on-`SourceInner`/`SourceText`/`TerminalSource`; the **existence of a shared formatter** — comment
2b — is settled as `format_source_line` in §2.10.)*

---

## 7. Forced compromises (explicitly flagged per the brief)

The prior draft flagged the **line/col duplication** as a forced compromise. **It is no longer one** —
§2.5 moves `LineColPos` + the bisect into `fltk-cst-core`, giving a single shared `resolve_line_col`
reached by the parser wrapper, the pyo3 span, and the pure-Rust span helper. No new Cargo edge, no
cycle. The rejected alternatives:

- **Make `fltk-cst-core` depend on `fltk-parser-core`** — inverts the existing direction
  (`parser-core → cst-core`), creating a cycle. Rejected.
- **Add an `fltk-native → fltk-parser-core` edge and keep the logic up in `parser-core`**
  (exploration §A.4 Option 2) — preserves edge direction but pulls a non-pyo3 crate into the cdylib link
  and violates the deliberate `native ↛ parser-core` separation; the cdylib grows. Rejected in favor of
  the move-down.
- **Extract a third `fltk-source-core` crate** (exploration §A.4 Option 3) — mechanically correct but
  maximum disruption (moves the established pyo3-linked `SourceInner`/`SourceText`). Rejected; the
  move-down achieves single-location with far less churn.

Two items remain that the design *consciously accepts* (neither is a duplicated algorithm):

1. **Python recomputes line-ends per `Span.line_col()` call; Rust caches on `SourceInner`.** The Python
   `Span` (frozen + slots, carrying a raw `str`) cannot reach a line-ends cache, so `Span.line_col()`
   recomputes O(N) per call; the Rust backend caches on `SourceInner.line_ends` (§2.6.3), amortizing to
   O(log N_lines) per call after the first scan. This is a **performance** asymmetry only — the returned
   `(line, col, line_span)` is identical (exploration-codepoint-efficiency §4 confirms Python `str`
   indexing is codepoint-native, so no correctness gap). Accepted because error reporting is cold.
   *Optional follow-up:* the Python `SourceText` already gains a `_filename` field in this change; a
   parallel `_line_ends` cache on `SourceText` threaded through `with_source` would let the Python span
   cache too — deferred as not worth the added `with_source` plumbing for a cold path. Captured as
   `TODO(py-span-linecol-cache)`.

2. **Two line-ends tables over the same source** (`TerminalSource.line_ends` and the new
   `SourceInner.line_ends`) — duplicated *state*, not duplicated *code* (the building/bisect logic is
   the single shared `resolve_line_col`). Both derive deterministically from immutable `text`, so they
   cannot disagree; the cost is a few words of memory per parser-produced source. Accepted; a follow-up
   could point `TerminalSource::pos_to_line_col` at `&self.source.inner.line_ends` and drop its own
   field. Captured as `TODO(linecol-cache-consolidate)`.

**TODO protocol (CLAUDE.md "TODO System").** The two `TODO(...)` comments above each require a paired
`TODO.md` entry under the matching slug (`py-span-linecol-cache`, `linecol-cache-consolidate`),
describing the concrete follow-up and naming the code location, or the burndown ground-truth audit
fails. Both are genuine, deferrable, "done is obvious" items — not vague aspirations.

No other spot forces a compromise: the protocol methods, the filename threading, the moved single-source
line/col logic, the error formatter, and the pyi stub are all clean and additive (regen of **both** the
Python and Rust parsers excepted, which is the project's normal flow, not a compromise).
