# Design review notes — `spanprotocol-native-linecol`

Adversarial fact-check of `design.md` against `request.md`, `exploration.md`, and source at
`c03a8012`.

## Verification performed (all passed)

The design's load-bearing claims were independently re-verified, not taken on faith:

- **The central feasibility probe was re-run by this reviewer.** A probe replicating the exact
  proposed shape (structural `LineColPosProtocol` with read-only `line`/`col`/`line_span: SpanProtocol`
  properties; `SpanProtocol.line_col`/`line_col_or_raise` retyped to the protocol; zero changes to
  `terminalsrc.py` or `fltk/_native/__init__.pyi`) was checked with the repo's locked pyright
  1.1.402 (`uv.lock:246-247`) via the same `uv run --group lint --group test pyright` invocation
  `make check` uses (`Makefile:89`): **0 errors** — both `terminalsrc.Span` and `fltk._native.Span`
  assignable to the retyped `SpanProtocol`, both backends' `line_col` results assignable to
  `LineColPosProtocol`. The control probe (native `Span` into the *current* `SpanProtocol`)
  reproduces exploration §3's `"line_col" is an incompatible type` error. The design's "verified
  feasibility" section is accurate, including the recursive-protocol resolution.
- Source citations check out: TODO block at `span_protocol.py:87-96`; `line_col`/`line_col_or_raise`
  at `span_protocol.py:97,105`; docstring guidance at `span_protocol.py:18-23`; `AnySpan` try-block
  is the module's sole `fltk._native` reference (lines 119-124; design says 118-123 — trivial
  off-by-one, content accurate); `terminalsrc.LineColPos` is a frozen dataclass with the field
  triple; native `LineColPos` in `__init__.pyi:14-28` exposes the triple as properties plus
  `__eq__`/`__hash__`.
- `error_formatter.py:92-119` touches only `lc.line`, `lc.col`, `lc.line_span.text()`, and
  `span.filename()` — all on the proposed protocols; the "type-checks unchanged" claim holds.
  `errors.py` (`format_error_message`, ~line 130) uses concrete `TerminalSource.pos_to_line_col` and
  never names the protocol — unaffected, as claimed.
- No generated file names `LineColPos`: repo grep confirms only `span_protocol.py`,
  `terminalsrc.py`, `fltk/_native/__init__.pyi` name it. The "generated artifacts untouched" claim
  holds.
- `TODO.md:28` entry exists with both paragraphs the design's bookkeeping removes; the code comment
  and master-list entry are the only two TODO locations (matches exploration §1), so the design's
  removal plan satisfies CLAUDE.md's two-piece TODO discipline.
- `test_span_protocol_assignability.py:33` is the Python-backend pin; docstring lines 14-16 contain
  the "deliberately NOT assigned" paragraph the design inverts. `import fltk._native` at module top
  of that test file works extension-absent (namespace-package portion; `.pyi` layout note lines 2-7),
  so `_rust_available = hasattr(...)` plus `if _rust_available:` pin placement is sound, and pyright
  does check the guarded branch body.
- New guard test under `fltk/fegen/pyrt/` is inside both pyright scope (`pyproject.toml`
  `include = ["fltk", "*.py"]`) and pytest collection (no `testpaths` restriction in `pytest.ini`).
- **Deviation from request.md's "touches exactly three hand-written files" is legitimate and
  verified.** Exploration §6's parenthetical (concrete backend annotations "would change... to keep
  both backends' concrete methods assignable") is disproven by the probe: return-type covariance
  makes the concrete `LineColPos` annotations conform unchanged. The design flags the refinement
  explicitly, and keeping concrete annotations is the CLAUDE.md-correct choice (no annotation
  churn for consumers pinned to a concrete backend). Request.md's "zero `fltk._native` names"
  constraint is correctly read per exploration §5 (protocol surface native-free; the pre-existing
  runtime `AnySpan` try-import stays).

## Findings

### design-1: The stub-stability guard as specified can be evaded by an aliased native import — including via the alias that already exists in the module

**Section:** "New stub-stability guard: `fltk/fegen/pyrt/test_span_protocol_native_free.py`"

**Quote:** "Assert no identifier, attribute chain, or string annotation anywhere within either
class body contains `_native`. Assert the module's only `fltk._native` import is the runtime
`AnySpan` fallback: every `import`/`ImportFrom` of `fltk._native` must sit inside a `Try` node,
and none may appear under `if TYPE_CHECKING:`."

**What's wrong:** The two assertions have a joint gap: a name *bound by* a legal (try-enclosed)
`fltk._native` import and then *referenced* inside a protocol class body passes both checks. The
module already contains exactly such a binding — `from fltk._native import Span as _RustSpan`
(`span_protocol.py:120`). A future edit that extends that try-import (e.g. `from fltk._native
import LineColPos as _RustLineColPos`) and uses the alias in a class-body annotation string
(`def line_col(self) -> "_RustLineColPos | None"`) satisfies the guard: the import sits inside a
`Try` and not under `TYPE_CHECKING` (check 2 passes), and the class-body text `_RustLineColPos`
does not contain the substring `_native` (check 1 passes — the design scopes it to identifiers/
attribute chains/string annotations containing `_native`, but an import alias can be named
anything). Such an annotation would even "work" at runtime when the extension is present, making
it a plausible accidental change, not just an adversarial one.

**Why (source-backed):** `span_protocol.py:119-124` shows the try-import alias pattern already in
the module; the whole point of the guard per the design's own root-cause section is that the D5.1
stub-stability argument is *transitive* and no other test can see a leak inside `span_protocol.py`
(exploration §5, `design-delta-python-rust-isolation.md` D5 item 1 as cited there).

**Consequence:** The exact regression the guard exists to catch — `SpanProtocol`'s or
`LineColPosProtocol`'s structural surface becoming native-dependent, making every generated-pipeline
consumer's pyright behavior stub-sensitive — slips through with all tests green. The request.md
load-bearing constraint ("the fix must add a stub-stability guard" for the transitive property)
would be satisfied in letter but not in force.

**Suggested fix:** Add a third assertion closing the alias channel: collect every name bound by any
`fltk._native` import anywhere in the module (the `asname`-or-`name` of each alias), then assert
none of those names is referenced within either protocol class body — as an `ast.Name`/attribute
root or as a token inside any string annotation. This keeps the guard scoped (class bodies only, so
the legitimate `AnySpan` use of `_RustSpan` below the classes stays legal) while making the
native-free property hold by name resolution rather than substring luck.

No other findings. The design is thoroughly grounded; every substantive claim checked was
verified against source or reproduced with the locked toolchain.
