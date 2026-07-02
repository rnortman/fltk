# Exploration: `TODO(py-span-linecol-cache)`

Facts and source ground truth only. No prescriptions.

## 1. TODO.md entry (verbatim ground truth)

`TODO.md:66-68`:

```
## `py-span-linecol-cache`

Python `Span.line_col()` recomputes the O(N) line-ends scan on every call because the
frozen-slots Python `Span` carries only a raw `str` and cannot reach a mutable cache.
The `SourceText` dataclass already gains a `_filename` field in the span-line-col-api
change; a parallel `_line_ends` list on `SourceText` threaded through `with_source`
would let the Python span amortize the scan the same way the Rust backend does via
`SourceInner.line_ends`. Deferred because error reporting is a cold path and the added
`with_source` plumbing is non-trivial. Location: `fltk/fegen/pyrt/terminalsrc.py:133`
(`Span.line_col` implementation).
```

## 2. Code-level `TODO(slug)` markers found

Repo-wide grep for the literal string `TODO(py-span-linecol-cache)` returns exactly
**one** code hit (all other hits are prose references inside
`docs/adr/2026/06/15-span-line-col-api/*.md`, the ADR that created this TODO):

- `fltk/fegen/pyrt/terminalsrc.py:133-136`:

  ```python
  # TODO(py-span-linecol-cache): recomputed on every call (O(N) scan). A future
  # optimization would cache line_ends on SourceText and thread it through
  # with_source. Out of scope for the span-line-col-api change; error paths
  # are cold. See docs/adr/2026/06/15-span-line-col-api/design.md §7.
  ```

  This sits directly above the line-ends build at line 137, inside `Span.line_col()`
  (method spans lines 113-158).

## 3. Does the code match each factual claim in the TODO?

### "frozen-slots Python `Span`"

`fltk/fegen/pyrt/terminalsrc.py:51` — `@dataclass(frozen=True, eq=True, slots=True) class Span:`.
Confirmed: frozen and slots both set.

### "carries only a raw `str`"

`fltk/fegen/pyrt/terminalsrc.py:57` — `_source: str | None = field(default=None, repr=False, compare=False, hash=False)`.
The field is typed `str | None`, not `SourceText | None`. `Span.with_source`
(`terminalsrc.py:211-232`) unwraps whatever it's given down to a raw string before
storing it: for a `SourceText` input it does `raw: str = source._text` (line 224) and
discards the `SourceText` wrapper object itself, keeping only `_text` and `_filename`
(`fn: str | None = source._filename`, line 225) as two separate primitive fields on the
constructed `Span` (`_source`, `_source_filename`). No reference to the originating
`SourceText` instance survives past `with_source`. Confirmed: `Span` cannot reach back
to a `SourceText`-held cache because it never keeps a handle to one.

### "recomputes the O(N) line-ends scan on every call"

`fltk/fegen/pyrt/terminalsrc.py:137` — inside `line_col()`, unconditionally on every
invocation: `line_ends = [idx for idx, c in enumerate(src) if c == "\n"]`. There is no
cache check before this line and no memoization decorator on the method. Each call to
`line_col()` re-scans the entire source string from scratch. Confirmed.

Contrast: `TerminalSource.pos_to_line_col` (`terminalsrc.py:267-296`), a separate,
older code path, does cache: `if not self.line_ends:` (line 273) guards the identical
scan-and-append logic and stores the result on `self.line_ends` (a plain mutable
instance attribute — `TerminalSource` is a regular non-frozen, non-slotted class,
`terminalsrc.py:245-250`). This confirms the TODO's cross-reference: the caching
pattern already exists in this file for a different type, just not one reachable from
`Span`.

### "`SourceText` dataclass already gains a `_filename` field"

`fltk/fegen/pyrt/terminalsrc.py:8-24` — `SourceText` is `@dataclass(frozen=True, slots=True)`
with fields `_text: str` (line 19) and `_filename: str | None` (line 20), set via a
custom `__init__` (lines 22-24) rather than the dataclass-generated one. Confirmed
present exactly as described.

### "the Rust backend does via `SourceInner.line_ends`"

Not verified in this pass (out of scope — the task asked about the Python side; the
worktree also contains a stray `.claude/worktrees/agent-ab295be24eef6e7ce/` copy of the
Rust crates from an unrelated in-flight agent run, which was excluded from all greps
above to avoid contaminating results with a second, possibly-diverged checkout).

## 4. What would "thread `_line_ends` through `with_source`" actually touch?

### Call sites of `Span.with_source(...)`

Grep for the literal call pattern `Span.with_source(` (excluding the stray
`.claude/worktrees/` copy) returns **1126** call sites across **22** files. Two
populations:

1. **Generated parser code** (the bulk of the 1126): every terminal/rule
   span-construction point in every generated parser —
   `fltk/fegen/bootstrap_parser.py`, `fltk/fegen/bootstrap_trivia_parser.py`,
   `fltk/fegen/fltk_parser.py`, `fltk/fegen/fltk_trivia_parser.py`,
   `fltk/fegen/regex_parser.py`, `fltk/fegen/regex_trivia_parser.py`,
   `fltk/unparse/toy_parser.py`, `fltk/unparse/toy_trivia_parser.py`,
   `fltk/unparse/unparsefmt_parser.py`, `fltk/unparse/unparsefmt_trivia_parser.py` — plus
   the generator template that emits this call shape, `fltk/fegen/gsm2parser.py:304`
   (docstring) and `:321` (emission site: `Emits
   fltk.fegen.pyrt.terminalsrc.Span.with_source(start, end, self._source_text)``).

   In every one of these generated-parser call sites, the third argument is the same
   expression, `self._source_text` — a single `SourceText` instance constructed once
   per parser instance (`fltk/fegen/bootstrap_parser.py:17`:
   `self._source_text = fltk.fegen.pyrt.terminalsrc.SourceText(...)`) and reused for
   every span produced during that parse. `fltk/fegen/gsm2parser.py:108,128-177`
   confirms this is a generator-emitted `def_field` initialized once in `__init__`, not
   re-constructed per call.

2. **Test code**: `tests/test_span.py`, `tests/test_span_protocol.py`,
   `tests/test_rust_span.py`, `tests/test_rust_cst_poc.py`,
   `tests/test_phase4_fegen_rust_backend.py`, `tests/test_fegen_rust_cst.py`,
   `tests/test_error_formatter.py`, `tests/test_clean_protocol_consumer_api.py`,
   `fltk/unparse/test_is_span_guard.py`,
   `fltk/fegen/pyrt/test_span_protocol_assignability.py`. These mix `SourceText`
   arguments and **raw `str` literals** passed directly, e.g. `Span.with_source(6, 11,
   "hello world")` (`tests/test_span.py:62`), `Span.with_source(0, 5, "hello")`
   (`tests/test_span.py:82`), `terminalsrc.Span.with_source(1, 5, "hello world")`
   (`tests/test_clean_protocol_consumer_api.py:802`). `Span.with_source`
   (`terminalsrc.py:226-228`) explicitly supports a bare `str` as "Python-backend
   convenience, preserved for backward compatibility" (docstring, lines 215-217) — this
   is a real, exercised code path, not a hypothetical.

Because every generated-parser call site already funnels through the one shared
`self._source_text` object, a cache keyed to that object's identity would be visible to
every span produced by one parser without changing the 1126 call sites' argument lists.
The `str`-argument path (population 2) has no comparable shared object to hold a cache
on — a bare string has no attribute slot to cache into, and repeated raw-`str` calls
pass whatever string literal or variable the caller wrote, with no `SourceText` wrapper
in the picture at all.

## 5. Is `line_col()` genuinely cold-path only, or are there hot callers?

Grep for `.line_col(` / `.line_col_or_raise(` across the Python tree (excluding the
stray worktree copy) finds callers in exactly two production (non-test) files:

- `fltk/fegen/pyrt/terminalsrc.py` — the method's own definitions
  (`line_col`, `line_col_or_raise`, lines 113-178) and `LineColPos` (line 239-242,
  the return type, no additional call).
- `fltk/fegen/pyrt/error_formatter.py:92` — `lc = span.line_col_or_raise()`, inside
  `format_source_line(...)` (defined at line 67), the module's only public function
  (module docstring at lines 1-13: *"Provides `format_source_line`, a backend-agnostic
  function that renders the ... "*).

`format_source_line` itself is called from **nowhere in production code** — grep for
`format_source_line\b` across the repo (excluding the stray worktree copy) returns hits
only inside `error_formatter.py` (its own definition/docstring) and
`tests/test_error_formatter.py` (all ~35 call sites are `format_source_line(...)`
assertions in that one test file).

This is a different, and more heavily used, path from the one that actually backs
in-tree parse-failure error messages: `fltk/fegen/pyrt/errors.py:126-131`,
`format_error_message(...)`, calls `terminals.pos_to_line_col(tracker.longest_parse_len)`
(line 131) — i.e. `TerminalSource.pos_to_line_col`, the *cached* legacy method
(§3 above), not `Span.line_col()`. `format_error_message` is invoked from
`fltk/plumbing.py:54,193,223`, `fltk/fegen/genparser.py:54`, and
`fltk/unparse/genunparser.py:40,69,97` — all inside `except`/failure branches that run
once per failed parse attempt, not in any per-token or per-alternative loop.

So: `Span.line_col()` / `line_col_or_raise()` have exactly one production caller
(`error_formatter.format_source_line`), and that function in turn has zero production
callers in this repository — it is exercised only by its own test file and (per its
docstring, lines 1-13) exists as a public, backend-agnostic formatting helper for
consumers (in-tree or out-of-tree) that hold a `Span` and want a rendered
"file:line:col: message" string. No in-tree hot loop (parsing, CST construction, or the
existing error-reporting path actually wired into the generated parsers) calls
`Span.line_col()`. This is consistent with the TODO's "error reporting is a cold path"
claim for everything currently wired up in-tree; it does not by itself establish call
frequency for out-of-tree consumers who might call `format_source_line` per-diagnostic
in a batch/lint-style tool (which would still be bounded by the number of
diagnostics/errors, not by parse volume).

## 6. Design-doc cross-reference

`docs/adr/2026/06/15-span-line-col-api/design.md:894-905` (§7 item 1) states the same
claim set as TODO.md verbatim in substance: Python `Span` (frozen + slots, raw `str`)
cannot reach a line-ends cache; Rust caches on `SourceInner.line_ends`; this is a
"performance asymmetry only" with identical returned values on both backends; "accepted
because error reporting is cold"; and explicitly proposes the same follow-up ("a
parallel `_line_ends` cache on `SourceText` threaded through `with_source`") captured
as `TODO(py-span-linecol-cache)`. Lines 914-917 record the TODO-protocol requirement
(paired `TODO.md` entry) as met for this slug.
