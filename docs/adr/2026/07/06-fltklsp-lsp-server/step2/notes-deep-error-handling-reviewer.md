# Deep error-handling review — Round 2 (M2 fltk-lsp)

Base 9719bab7 .. HEAD d9ab841. Lane: error observability and response only.

Scope reviewed: `fltk/lsp/server.py`, `server_cli.py`, `engine.py`, `features.py`,
`positions.py`, and the `plumbing.py`/`plumbing_types.py` `error_pos` addition.

---

## errhandling-1 — Format path's initial `parse_text` is unguarded; a raise escapes as a raw LSP error

`fltk/lsp/server.py:305` (inside `_format_blocking`).

The broken error path: step 1 of the format pipeline,
`parsed = plumbing.parse_text(self._fmt_parser, text, self._start_rule)`, is **outside**
any `try`. Only steps 2–3 (unparse/render at 309-314 and verify-reparse at 315-319) are
wrapped. `plumbing.parse_text` runs the generated recursive-descent parser and does **not**
catch `RecursionError` — this is exactly why `engine.analyze` (`engine.py:141-160`) wraps
its own `parse_text` call in `except RecursionError`. The format path has no such guard on
its first parse.

Why it matters: a document that is deeply nested but otherwise valid makes the generated
parser recurse past the interpreter limit. `RecursionError` (and any other unexpected raise
from `parse_text`) propagates out of `_format_blocking`, out of the executor future awaited
in `format_document` (server.py:336), out of the `formatting` handler (server.py:416-418),
and pygls turns it into a JSON-RPC error response.

Consequence: design §4.8 states formatting failures "must degrade to 'no edits + log',
never a raw LSP request error." This path violates that guarantee. On a deeply-nested valid
document the user gets an opaque LSP request failure (editor error popup) instead of a
silent no-op plus a `window/logMessage` breadcrumb. It is also inconsistent with `analyze`,
which turns the same input into a clean diagnostic — the same document diagnoses fine but
crashes the formatter. On-call sees a request error with no formatter log line explaining it.

What must change: wrap the step-1 `parse_text` in the same `except Exception` treatment as
steps 2–3 (log + `return None, logs`), or extend the existing guard to cover it. The
`RecursionError` case specifically should be caught symmetrically with `engine.analyze`.

---

## errhandling-2 — `_encoding()` silently coerces any non-utf32 advertised encoding (incl. utf-8) to utf-16, with no guard

`fltk/lsp/server.py:127-132`, depending on `_constrain_pygls_encodings` at `45-59`.

The broken error path: `_encoding()` returns `UTF32` only when the advertised
`workspace.position_encoding` is exactly `Utf32`; **every other value** — `utf-8`, `None`,
or any unknown string — falls through to `return PositionEncoding.UTF16`. `LineIndex` does
not implement utf-8, so utf-16 column math is silently substituted whenever the advertised
encoding is anything the two-value model does not expect.

The only thing preventing utf-8 from ever being advertised is the import-time monkeypatch
`_pygls_capabilities._SUPPORTED_ENCODINGS = frozenset({Utf16, Utf32})`. This works against
today's pygls (its `choose_position_encoding` reads that module global at call time,
verified in `.venv/.../pygls/capabilities.py:82-90`), but it is an assignment to a private
symbol: if a future pygls renames or restructures that global, the assignment **silently
creates a dead attribute** (assignment never raises), pygls resumes offering utf-8, a utf-8
client gets utf-8 negotiated, and `_encoding()` coerces it to utf-16 with no complaint.

Consequence: the entire coordinate system's correctness rests on a private-symbol
monkeypatch, and the read-back guard that §4.5 promised ("reads that one advertised value
back") does not actually validate the value is computable. If utf-8 ever slips through, every
emitted semantic-token position, diagnostic range, folding/selection range, and format-edit
range is computed in utf-16 units while the client is told utf-8 — silent, and invisible for
ASCII-only text (utf-8 and utf-16 code-unit counts agree there), only diverging once a
document contains any non-ASCII character. This is precisely the coordinate-mixing bug class
§4.5 says the single-owner design exists to rule out; the fallback branch reintroduces it.
On-call sees "highlights/folds drift on files with accented characters" with no log line.

What must change: make `_encoding()` assert/verify the advertised value is one of
`{Utf16, Utf32}` and log loudly (or fail) on anything else, rather than treating the entire
non-utf32 space as utf-16. The impossible-in-theory utf-8 case should be reported if it ever
becomes reachable, not silently absorbed.

---

## errhandling-3 — Debounced analysis is fire-and-forget; a non-`RecursionError` analysis exception vanishes with no report

`fltk/lsp/server.py:247` (`schedule_debounced` →
`asyncio.ensure_future(self._debounced_analyze(uri))`), `231-240`, `224-229`; engine guard
at `engine.py:141-160`.

The broken error path: the didChange push path schedules `_debounced_analyze` as a bare
`ensure_future` task that nothing awaits and that has no done-callback inspecting its result.
`_debounced_analyze` → `analyze_and_publish` → `_analysis_for` → `await future`, where the
future runs `_analyze_blocking` → `engine.analyze`. `engine.analyze` catches **only**
`RecursionError`; `classify.classify` (and the generated parser) can raise other exceptions
— `KeyError`/`AttributeError`/`TypeError` from generated code or a classifier/config drift,
the same silent-bug family as the unparser issue in c0534e3. Such an exception propagates
back through `await future` into the orphaned task.

Consequence: the exception is neither published as a diagnostic nor sent via
`window/logMessage`; it surfaces only as asyncio's "Task exception was never retrieved" on
stderr at GC time — not in the LSP client's server log, and unreliably timed. The document's
diagnostics simply stop updating (the last publish stands) with no breadcrumb the operator
can find. The format path deliberately catches broad `Exception` and logs (server.py:283,
312, 317) precisely to avoid this; the analysis push path has no equivalent, so the same
class of generated-code bug is loud in one path and silent in the other. On-call cannot
diagnose "diagnostics froze on this file."

What must change: either broaden `engine.analyze` to convert unexpected exceptions into a
`ParseErrorInfo`/logged failure (as it does for `RecursionError`), or wrap the debounce
task body so any exception is reported via `window/logMessage` rather than swallowed by the
orphaned task.

---

## errhandling-4 — Unknown token type/modifier silently dropped with no log or assert (design specified "assert-level")

`fltk/lsp/features.py:69-80` (`_modifier_bits`) and `120-124` (`encode_semantic_tokens`
`type_index is None: continue`).

The broken error path: `_modifier_bits` does `_MODIFIER_BIT.get(modifier)` and skips on
`None`; `encode_semantic_tokens` does `_TYPE_INDEX.get(token.token_type)` and `continue`s on
`None`. Both branches are the "impossible in theory — `classify` only emits legend members"
case (per the comments and design §4.6). Neither branch asserts nor logs; it is a bare
silent drop.

Consequence: design §4.6 called for "a defensive assert-level check" — an `assert` would at
least fire under test/`-O`-off and localize a legend/classifier drift. As written, if
`classify` ever emits a type or modifier not in the legend (a real drift bug when the token
set and the `features.py` tuples fall out of sync), the affected token silently loses its
color, or a modifier silently disappears, with zero observability — no diagnostic, no log,
no assertion. The whole document keeps rendering, so nothing looks broken; the drift is
invisible until someone notices one construct is uncolored and has no server-side signal to
trace it to. This is an invariant violation that is responded to (drop-and-continue, correct)
but never reported.

What must change: replace the silent `continue`/skip with at least an `assert` (matching the
design's stated intent) or a one-time `window/logMessage`/logger warning naming the offending
type/modifier, so a legend↔classifier drift leaves a breadcrumb rather than a silently
half-painted document.

---

## Adjacent, left to other lanes

- `server.py:231-247`: `_debounced_analyze`'s `finally: self._debounce.pop(uri, None)`
  removes whatever task currently occupies the slot, which after a re-`schedule_debounced`
  is the *replacement* task — corrupting the debounce bookkeeping so a later reschedule can
  no longer cancel it (duplicate analyses, both version-guarded). Cancellation-path logic
  bug, but the consequence is redundant work, not a swallowed error → correctness-reviewer.
</content>
</invoke>
