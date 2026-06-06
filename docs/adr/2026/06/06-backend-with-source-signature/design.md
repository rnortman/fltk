# Design: backend-with-source-signature

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope is fixed by `request.md`. This doc does not restate it. Where `request.md`
and this design disagree, `request.md` wins.

## Root cause / context

`Span.with_source` has a divergent third-parameter type across backends:

- Python: `with_source(cls, start: int, end: int, source: str)` —
  `fltk/fegen/pyrt/terminalsrc.py:114-117`. Stores the raw `str` in the
  `_source` field (`terminalsrc.py:38`).
- Rust: `with_source(_cls, start, end, source: &SourceText)` —
  `src/span.rs:115-123`, where `SourceText` is a `#[pyclass(frozen)]` wrapping
  `Arc<SourceInner>` (`src/span.rs:29-47`). Constructed from Python as
  `SourceText(text)` (`src/span.rs:39-46`).

The backend selector `fltk/fegen/pyrt/span.py` re-exports `Span` from either
backend, but sets `SourceText: type | None = None` on the Python path
(`span.py:14`) and only binds a real `SourceText` from `fltk._native` on the
Rust path (`span.py:17`). Consequence: code written against the selector
(`from fltk.fegen.pyrt.span import Span`) cannot construct a source-bearing span
portably. Under the Rust backend, `Span.with_source(s, e, "raw str")` raises
`TypeError` (PyO3 rejects `str` for `&SourceText`); under the Python backend,
`SourceText` is `None` and cannot be referenced at all. The exploration
corrected the original TODO wording: the failure is a noisy `TypeError`, not
silent (`exploration.md:17-23`).

There are zero in-tree production callers of `with_source`
(`exploration.md:40-48`); the affected parties are out-of-tree consumers, who
per `CLAUDE.md` are first-class. Forcing them to branch on `SourceText is not
None` violates the project's "near-drop-in replacement" goal.

Per user direction (`request.md:13-18`): unify on `SourceText` as the portable
type by fixing the Python adapter layer; Rust stays `SourceText`-only.

## Proposed approach

Three edits, all on the Python side. No Rust, no parser, no generator, no
protocol changes.

### 1. Add `SourceText` to the Python backend (`terminalsrc.py`)

Add a small `SourceText` class — a thin immutable wrapper over `str` that
mirrors the Python-visible surface of the Rust `SourceText` needed for span
construction:

- Construct from a `str`: `SourceText(text: str)`.
- Expose the underlying text so `with_source` can store it (e.g. a `.text`
  property / attribute) so `with_source` can store it. The Rust class does
  **not** expose its text publicly, so the only contractually-portable operation
  is construction. Whether the Python wrapper's text accessor is public or
  private is Open Question 1; the default is private.

Shape: `@dataclass(frozen=True, slots=True)` holding the source `str`,
consistent with the existing `Span`/`LineColPos` dataclasses in the file. Frozen
mirrors the Rust `#[pyclass(frozen)]`.

### 2. Make Python `with_source` accept `str | SourceText`

Change `terminalsrc.py:114-117`:

```
def with_source(cls, start: int, end: int, source: str | SourceText) -> "Span":
```

Normalize: if `source` is a `SourceText`, unwrap to its `str` before storing in
`_source`; if it's a `str`, store directly (preserves existing behavior and the
"no copy" property the current docstring advertises). The stored `_source`
remains a `str`, so `text()`, `text_or_raise()`, `merge`, `intersect`, and
`_coerce_source` (`terminalsrc.py:41-112`) are unchanged and keep working.

This keeps existing `Span.with_source(0, 5, "hello")` callers working
(non-breaking constraint, `request.md:22-23`; exercised by
`tests/test_span_protocol.py:19`).

### 3. Export `SourceText` from the selector on the Python path (`span.py`)

Replace `SourceText: type | None = None` (`span.py:14`) with an import of the
real Python `SourceText` from `terminalsrc`. The Rust path
(`span.py:16-22`) still overwrites `SourceText`/`Span`/`UnknownSpan` from
`fltk._native` when available, so the Rust `SourceText` wins under that backend.
After this, `from fltk.fegen.pyrt.span import Span, SourceText` resolves to a
real class under both backends, and `SourceText` is never `None`.

Update `span.py` docstring (`span.py:3-7`): remove the
`TODO(backend-with-source-signature)` line and the "branch on `SourceText is not
None`" guidance, since that branch is no longer required. Keep the note that
`with_source` is intentionally excluded from `SpanProtocol` (it remains a
backend-concrete constructor, not a protocol member —
`request.md:25`). The `__all__` (`span.py:24`) already lists `SourceText`.

### Portable contract after the change

- Portable construction: `Span.with_source(start, end, SourceText(text))` works
  on both backends.
- Python-only convenience: `Span.with_source(start, end, "raw str")` continues
  to work on the Python backend. It still raises `TypeError` on the Rust
  backend — unchanged, and acceptable: the portable form is the `SourceText`
  form, and Rust is deliberately not given `str` acceptance (`request.md:24`).

### Type surface (`AnySpan` / annotations)

No change needed. `SpanProtocol` and `AnySpan` (`span_protocol.py`) do not
mention `SourceText` or `with_source`. `AnySpan` already unions the Python and
Rust `Span` types (`span_protocol.py:59-64`). No downstream annotation churn.

## Edge cases / failure modes

- **`str` under Rust backend.** Still `TypeError`. Intentional and documented;
  not a regression. The portable path is `SourceText`.
- **Cross-backend `SourceText` equality.** Explicit non-goal (`request.md:26`).
  The Python `SourceText` need not compare equal to a Rust `SourceText`. Frozen
  Python dataclass gives value-equality over `text`; the Rust class compares by
  its own `#[pyclass]` semantics. No source-bearing span flows anywhere today,
  so this is latent. The design does **not** attempt cross-backend `SourceText`
  equality and callers must not assume it.
- **Cross-backend source-bearing span equality.** Out of scope and not relied
  on. Both backends already exclude `_source`/`source` from `Span` equality and
  hash (`terminalsrc.py:38`, `src/span.rs:71-84`), so a source-bearing span
  equals a sourceless span at the same coords on each backend independently;
  this design changes nothing here.
- **`with_source` given a non-`str`, non-`SourceText`.** Python path: passing an
  arbitrary object would currently be stored silently as `_source` and fail
  later in `text()`. With the normalization in edit 2, decide behavior — see
  Open Questions. Minimum: existing `str` and new `SourceText` both work; no new
  silent-failure mode is introduced relative to today.
- **Selector import when `fltk._native` is importable but partially broken.**
  Existing `try/except` (`span.py:16-22`) already warns and falls back to the
  pure-Python symbols, which now include a real `SourceText`. Strictly better
  than today (where fallback left `SourceText = None`).
- **`_source` storage type.** Stays `str`. The Rust `Arc`-sharing optimization
  has no Python analogue; the Python wrapper is a thin container, as
  `request.md:16` anticipates. No memory-semantics parity is promised.

## Test plan

Tests after the change (extend `tests/test_span_protocol.py`, which already owns
the backend-selector and cross-backend coverage):

1. **Selector exports `SourceText` on both backends.** `from
   fltk.fegen.pyrt.span import Span, SourceText`; assert `SourceText is not
   None` and is a class. Runs unconditionally (Python backend) and, when
   `fltk._native` is present, asserts the bound `SourceText` is the native one.
2. **Portable `SourceText` construction — Python backend.** Using the
   `terminalsrc` Python classes directly: `Span.with_source(6, 11,
   SourceText("hello world")).text() == "world"`.
3. **Portable `SourceText` construction — Rust backend** (skip if
   `fltk._native` absent). Mirror of test 2 via the native classes — largely
   already covered by `tests/test_rust_span.py:88-90`; add the
   selector-import variant to prove the portable path end-to-end.
4. **Backward compatibility — `str` still works on Python backend.**
   `Span.with_source(0, 5, "hello").text() == "hello"` (guards the non-breaking
   constraint; complements `test_span_protocol.py:19`).
5. **`SourceText` is frozen** (Python backend): assignment raises, mirroring the
   Rust `#[pyclass(frozen)]` contract.

Full gate: `uv run --group dev maturin develop` then `uv run pytest && uv run
ruff check . && uv run pyright` (`request.md:29`).

## TODO cleanup

- Remove the `TODO(backend-with-source-signature)` comment (`span.py:7`).
- Remove the `## backend-with-source-signature` entry from `TODO.md:11-13`.

The separate `.start`/`.end` exposure divergence and the parse-path wiring
(`exploration.md:30-38,50-54,66-72`) remain out of scope and keep their own
existing TODOs (e.g. `rust-cst-child-span-test`); this change does not touch
them.

## Open questions

1. **Should the Python `SourceText` expose its text publicly?** The Rust
   `SourceText` exposes no text accessor, so a public `.text` on the Python side
   would be a Python-only surface with no portable counterpart — a mild
   cross-backend asymmetry, but harmless and possibly convenient for
   Python-backend consumers. Default if unanswered: keep text access internal
   (private) to preserve the minimal portable contract (construct-only).

2. **Behavior of `with_source` on an unrecognized `source` type.** Options:
   (a) leave it permissive (store whatever is passed, fail later in `text()`, as
   today); (b) raise `TypeError` eagerly for anything that is not `str |
   SourceText`. Eager raising is friendlier and matches the Rust backend's eager
   rejection, but is a (minor) behavior change for any caller currently abusing
   the field. Default if unanswered: eager `TypeError`, for parity with Rust and
   to avoid deferred silent failures.
