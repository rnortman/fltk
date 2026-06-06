# Request: backend-with-source-signature

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** cross-backend API unification (Python adapter); small. Reframed/scoped from the original TODO.

**Background.** `Span.with_source(...)` has divergent signatures across backends:
- Python: `Span.with_source(cls, start: int, end: int, source: str)` — `fltk/fegen/pyrt/terminalsrc.py:115`.
- Rust: `Span.with_source(_cls, start: i64, end: i64, source: &SourceText)` — `src/span.rs:117`, where `SourceText` is a `#[pyclass(frozen)]` wrapping `Arc<SourceInner>` (`src/span.rs:29-46`).

So code importing `Span` via the backend selector (`fltk/fegen/pyrt/span.py`) cannot call `with_source` portably: passing a `str` raises `TypeError` under the Rust backend. `span.py` currently sets `SourceText: type | None = None` on the Python path and overwrites it from `fltk._native` on the Rust path. There are zero in-tree production callers of `with_source`; the affected parties are out-of-tree consumers who construct source-bearing spans by hand. This cuts against the project's "near-drop-in replacement" goal (downstream should not branch on backend).

**USER DIRECTION (verbatim — flag for downstream agents; do not second-guess or re-litigate):** "I don't understand why we can't just fix backend-with-source-signature right now? The Rust code can keep taking SourceText and the python adapter layer can fix that?"

**Fix shape (chosen, per user direction).** Unify on `SourceText` as the portable type by fixing the **Python adapter layer**; leave Rust unchanged.
- Add a `SourceText` class to the Python backend (`fltk/fegen/pyrt/terminalsrc.py`) — a thin wrapper over `str` providing whatever Python-visible surface parity is needed for span construction (construct from `str`; expose the source text).
- Export it from the `span.py` selector on the Python path (replace the `SourceText = None` with the real Python class), so `from fltk.fegen.pyrt.span import SourceText` works on both backends.
- Make Python `with_source` accept `str | SourceText` (keep `str` working for existing callers; add the `SourceText` form). Backend-portable code then uses `SourceText` (the cross-backend subset). **Rust stays `SourceText`-only.**

**Scope boundary (IMPORTANT — only the construction-API unification is in scope).** The deeper work of wiring source-bearing spans through the parse path, and the separate `.start`/`.end` exposure divergence (Rust `Span` deliberately omits `.start`/`.end`; Python `terminalsrc.Span` exposes them), are explicitly OUT OF SCOPE and are NOT blockers for this change. The triage previously conflated the two; they are decoupled here.

**Load-bearing constraints / non-goals.**
- Non-breaking: existing Python `Span.with_source(start, end, "raw str")` callers must keep working. Add `SourceText` support; do not remove `str` support.
- Rust code unchanged (per user). Do not add `str` acceptance to the Rust `with_source`.
- `with_source` is intentionally excluded from `SpanProtocol` (`span_protocol.py`) — keep it that way; this is a backend-concrete constructor, not a protocol member.
- **Explicit non-goal: cross-backend equality/hash of source-bearing spans.** Rust `Span` is `#[pyclass(eq, hash)]` over its fields incl. `source` (`Arc<SourceInner>`); the Python `SourceText` wrapper need NOT compare equal to a Rust `SourceText`, and source-bearing spans across backends need not be `==`. No source-bearing spans flow anywhere today, so this is latent — but the implementer MUST NOT assume cross-backend source-span equality holds, and should not try to make it hold.
- Do not change the generated parsers (they construct `terminalsrc.Span(start, end=-1)` directly and are out of scope).

**Verification.** `from fltk.fegen.pyrt.span import Span, SourceText` works under both backends; `Span.with_source(start, end, SourceText(text))` works under both; `Span.with_source(start, end, "raw str")` still works under the Python backend; a test exercises the portable `SourceText` path on the Python backend (and, if `fltk._native` available, the Rust path). `uv run pytest && uv run ruff check . && uv run pyright`. `TODO.md` entry and the `TODO(backend-with-source-signature)` comment (`span.py:7`) removed.

**Exploration:** `exploration.md` in this dir (note its correction: the failure is a noisy `TypeError`, not silent; and it documents the separate, out-of-scope `.start`/`.end` divergence).
