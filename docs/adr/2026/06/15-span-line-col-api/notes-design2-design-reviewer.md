# Design review (revision 2 — crate move + filename + formatter)

Scope of this pass: the NEW material (crate-layout move of `resolve_line_col`/`LineColPos` into
`fltk-cst-core`; optional `filename` threading; `format_source_line`; efficiency claims), fact-checked
against fltk source on branch `span-line-col-api` (base `8cd6232`) and the clockwork consumer at
`~/tps/clockwork`. The prior `line_col`/`line_col_or_raise`/`LineColPos` API surface was reviewed
previously and is not re-litigated except where the new scope changes it.

User comments in `notes-design-user.md` are authoritative; findings below do NOT fault the design for
honoring them — they fault places where the design's mechanism does not actually deliver what those
comments require, or where claims are unverified/wrong.

---

## design-1 — Rust-parser-produced spans never receive a filename; the design's "Rust caller entry point is the pyo3 SourceText ctor" does not cover the parsing path

Section: §2.8 "Because Rust callers do not get a pyo3 `TerminalSource` … the **Rust-backend caller
entry point for filename is the pyo3 `SourceText` constructor** — `SourceText(text, filename=None)`";
§2.9 cross-backend filename equivalence; §4.1 "build a source with a filename on each backend,
parse/construct a span, assert `span.filename()` matches"; exploration-scope-expansion §B.5 and Open
Q1.

What's wrong: On the Rust backend, parser-produced spans do not flow through a Python-constructed
`SourceText` at all. The generated Rust parser's pyo3 constructor takes a raw `str`:

- `crates/fegen-rust/src/parser.rs:1399-1407` — `PyParser::new(text: &str, capture_trivia, max_depth)`
  → `Parser::new(text, ...)`.
- `crates/fegen-rust/src/parser.rs:57-59` — `Parser::new(text: &str, …)` →
  `Self::from_source_text(SourceText::from_str(text), …)`.

So the `SourceText` that backs every Rust-parser span is built *inside* Rust from a `&str`; the Python
caller never sees or constructs it. clockwork's Rust path confirms this: `_RustParseBackend.parse`
calls `self._rparser_mod.Parser(source)` with a plain string
(`~/tps/clockwork/clockwork/dsl/ir/parser_backend.py:143`). There is no
`Parser.from_source_text`-style pyo3 entry that accepts a `SourceText` (only `PyParser.__new__(text)`;
`register_classes` adds just `PyParser`/`PyApplyResult`/`PyGrammar…`, parser.rs:1649-1651).

Adding an optional `filename` to the pyo3 `SourceText` ctor therefore does nothing for
**parser-produced** Rust spans — the ctor is not on that path. To actually put a filename on a
Rust-parser span, the design would also need to add a `filename` param to: the generated Rust
`PyParser::new`, `Parser::new` and `Parser::from_source_text` (`fegen-rust/src/parser.rs`), and the
**Rust-parser code generator** that emits those (not `gsm2parser.py`, which only emits the Python
parser). The design's §2.8 change list and §5/§7 ("regen required" = Python parsers only) omit the
Rust-parser generator entirely.

Consequence: The §4.1/§2.9 cross-backend equivalence test — "parse on each backend with a filename set,
assert `span.filename()` matches" — cannot pass on the Rust backend as designed, because there is no
way to set the filename on a Rust *parse*. Either the test is unimplementable as written, or it
silently degrades to only testing the hand-constructed `SourceText(text, filename)` path (not a real
parse), leaving the headline feature ("a parser-produced span can tell you its file") unmet on the Rust
backend — the exact thing comment 2 asks for, and the backend clockwork is porting *to*.

Suggested fix: Either (a) extend scope to thread `filename` through the Rust-parser generator +
`PyParser::new` + `Parser::new`/`from_source_text` (and call this out as additional regen of the Rust
parser, parallel to the Python regen), or (b) explicitly scope filename-on-span to the Python backend
+ hand-built Rust `SourceText` only, and state plainly that Rust *parser*-produced spans return
`filename() == None` until the Rust generator is updated — adjusting §2.9/§4.1 so the cross-backend
equivalence claim is not overstated.

---

## design-2 — `format_source_line` reads `lc.line_span.text()`, which is `None` on every Rust-parser span until design-1 is fixed; but also: the formatter's source-bearing-line_span guarantee is only as good as the line_col path

Section: §2.10 "the function calls … `lc.line_span.text() or ""`"; §2.4 "**both backends produce a
source-bearing `line_span`**"; §4.5 "Assert the full multi-line string literally" / "Cross-backend: the
same logical span/source on Python and Rust backends produces the **same** formatter output".

What's wrong: This finding is conditional on design-1. The formatter relies on `lc.line_span.text()`
returning the offending line. That works only when the span (and hence the `line_span` the shared
`resolve_line_col` builds from `self.source`) is source-bearing. For Rust-parser spans that is true for
the *span's* own source, so `line_col()` itself is fine — but the §4.5 "cross-backend produces the same
formatter output" assertion still needs a filename on the Rust side for the `In <file>:` header to
match, which design-1 shows is currently unreachable on a Rust parse.

Consequence: The cross-backend formatter-equivalence test (§4.5) will diverge in the header line
(`In <file>…` on Python vs `At line…` on Rust, since Rust-parse `filename()` is `None`) unless design-1
is resolved or the test is restricted to passing `filename=` explicitly on both backends. As written
the test will either fail or quietly only exercise the explicit-`filename=` precedence branch,
under-testing the headline `span.filename()` fallback path.

Suggested fix: Resolve design-1, or make §4.5's cross-backend case pass `filename=` explicitly on both
backends and add a separate Python-only case for the `span.filename()` fallback, with a note that the
Rust-parse fallback is pending the Rust-generator filename work.

---

## design-3 — Python `pos_to_line_col` has no `pos < 0` lower-bound guard, so the §4.4 / §4.3 "parity with TerminalSource.pos_to_line_col" anchor and the negative-start divergence story need care

Section: §2.1 "the shared helper inherits `pos_to_line_col`'s in-domain treatment of `pos = -1`";
§2.6.2 "`pos_to_line_col(-1)` still returns `LineColPos(line=0, col=-1)`"; §4.3/§4.4 drift anchor
"`span.line_col()` and `TerminalSource(src).pos_to_line_col(span.start)` agree for a source-bearing
span"; edge-case table row "Negative start, source attached".

What's wrong (factual): The two `pos_to_line_col` implementations do not have the same domain on the
low end, and the design's framing ("inherits `pos_to_line_col`'s treatment of `pos = -1`") glosses
over a Python-vs-Rust divergence the move-down does not touch:

- Rust `pos_to_line_col` (`crates/fltk-parser-core/src/terminalsrc.rs:182`) rejects `pos < -1`
  (returns `None`) and accepts `pos == -1` as the sentinel.
- Python `pos_to_line_col` (`fltk/fegen/pyrt/terminalsrc.py:183-205`) has **no negative guard at all**
  — only `pos > len` raises. `pos = -1` (and any negative `pos`) flows into `bisect.bisect_left`. For
  `-1` it yields `line=0, col=-1` (matching Rust at exactly `-1`), but for `pos < -1` Python does NOT
  return `None`/raise the way Rust does; it silently bisects a negative position.

The design's "shared `resolve_line_col`" only unifies the *Rust* side (§2.5 step 3 keeps Rust
`TerminalSource::pos_to_line_col` as a thin wrapper over the moved helper). The **Python**
`TerminalSource.pos_to_line_col` is explicitly left untouched (§2.5 final para, §2.6.1 is Rust-only).
So the Python `Span.line_col()` (new, with the `start < 0 → None` wrapper guard) and the Python
`TerminalSource.pos_to_line_col` (no guard) will **disagree** for any negative `start`: the span method
returns `None`, the `TerminalSource` method returns a `LineColPos`. The design's drift anchor (§4.4)
restricts itself to "a source-bearing span" agreement, which dodges this, but the edge-case table row
"Negative start, source attached → `line_col()` = `None`, … = filename of source" and §2.6.2's
divergence test are framed as Rust-only; the Python equivalent divergence is never stated.

Consequence: If the implementer writes the Python drift-anchor test over a negative-start span (a
natural "does the span method match the legacy method?" case), it fails — not because of a bug, but
because the two Python paths genuinely diverge and the design never says so. Lower-stakes than
design-1, but it is an unstated cross-method inconsistency that will surface during TDD and could be
mistaken for an implementation error.

Suggested fix: State explicitly that the new `start < 0 → None` guard makes `Span.line_col()` diverge
from the legacy `TerminalSource.pos_to_line_col` on **both** backends for negative positions (Rust at
`pos < -1`, Python at any `pos < 0`), and scope the drift anchor to non-negative source-bearing
positions on the Python side (as §4.4 already implicitly does), with the divergence pinned by a
deliberate test mirroring §2.6.2's Rust one.

---

## design-4 — `m.add_class::<LineColPos>()` registration path cites `src/lib.rs:14-15` but the import binding at `src/lib.rs:6` must also change, and the shim re-export claim should be verified against the actual file

Section: §2.6 step 1 "Registration path … 1. Export it from `fltk-cst-core/src/lib.rs:18` … 2.
Re-export through the extension shim `src/span.rs:2` … 3. Register with the module in `src/lib.rs:14-15`".

What's wrong (incomplete, not wrong): The three cited edits are individually accurate against source:

- `crates/fltk-cst-core/src/lib.rs:18` is `pub use span::{SourceText, Span, SpanError};` (confirmed).
- `src/span.rs:2` is `pub use fltk_cst_core::{SourceText, Span};` (confirmed — the shim re-export).
- `src/lib.rs:14-15` is `m.add_class::<Span>()?; m.add_class::<SourceText>()?;` (confirmed).

But the design omits that `src/lib.rs:6` is `use span::{SourceText, Span};` — the name binding the
`m.add_class::<LineColPos>()` call at step 3 depends on. Adding `LineColPos` to the `add_class` calls
without also adding it to the `use span::{…}` import at line 6 (or fully-qualifying it) will not
compile. Minor, but the design presents the registration path as exhaustive ("Without all three, …
names an unreachable type"), and as listed it is one edit short of compiling.

Consequence: A literal implementation of the three listed steps fails `cargo check` with an unresolved
`LineColPos` name in `src/lib.rs`. Caught immediately by the compiler, so low blast radius, but the
"required — otherwise unreachable" framing implies completeness it doesn't have.

Suggested fix: Add `src/lib.rs:6` (the `use span::{…}` import) to the registration step list, or note
that `LineColPos` must be brought into scope there.

---

## design-5 — `LineColPos` as `pyclass(frozen, eq)` with a `line_span: Span` getter: the `eq` derivation and getter return type are asserted but not grounded against pyo3 constraints

Section: §2.4 / §2.6 step 1 "`LineColPos` becomes a pyo3 pyclass … `#[cfg_attr(feature = "python",
pyclass(frozen, eq))]` with getters `line: int`, `col: int`, `line_span: Span`"; §2.11 "structurally
identical".

What's wrong (unverified): `pyclass(eq)` requires the Rust struct to derive/impl `PartialEq`. The
current Rust `LineColPos` derives `PartialEq, Eq` (`terminalsrc.rs:18`), and its `line_span: Span`
field's `Span` impls `PartialEq` ignoring source (`span.rs:176-180`), so a derived `LineColPos`
`PartialEq` is coherent. That part holds. What is NOT addressed: a `#[pyclass]` getter returning
`line_span: Span` (a pyclass by value) requires `Span: Clone` (it is — `#[derive(Clone)]` at
span.rs:156) and the getter to hand back an owned/cloned `Span`; the design says "getters … `line_span:
Span`" without specifying it returns a clone, and `pyclass(frozen, eq)` on a struct holding a `Span`
that is itself `pyclass(frozen, eq, hash, from_py_object)` is a pyclass-containing-pyclass-by-value
getter — workable in pyo3 0.29 but the design asserts it as trivial without confirming the getter form
(clone vs reference) or that `eq` on `LineColPos` is actually wanted (two `LineColPos` with
source-differing but value-equal `line_span` will compare equal, since `Span` eq ignores source — fine,
but unstated).

Consequence: Lower-stakes than design-1/2. If the implementer takes "getters: line_span: Span"
literally as a borrow-returning getter, it won't compile (can't return a bare `&Span` field from a
frozen pyclass as a Python value without cloning into a `Py<Span>`/owned `Span`). The design should
specify the getter returns an owned `Span` (clone, O(1) Arc bump) to avoid a wrong first implementation.

Suggested fix: Specify `line_span` getter returns an owned `Span` (clone). Confirm `pyclass(eq)` is the
intended equality (value-equal, source-ignoring) and note it, since it differs subtly from the Python
`@dataclass(eq=True)` `LineColPos` whose `line_span` equality also ignores source via `Span`
`compare=False` — they happen to agree, but only because both ignore source.

---

## design-6 — "no ABI-marker bump" claim is correct, but rests on `SourceText` holding only `Arc<SourceInner>`; verified — recording as confirmed, not a defect

Section: §2.6 step 3 "**ABI impact:** changing `SourceInner`'s layout does **not** move the
cross-cdylib ABI probe … `SourceText` holds only `Arc<SourceInner>` (one pointer) regardless of
`SourceInner`'s contents".

Verification: Confirmed correct. `SourceText { inner: Arc<SourceInner> }` (`span.rs:56-58`); the probe
measures `size_of::<<SourceText as PyClassImpl>::Layout>()` (`span.rs:128-137`, `lib.rs:57-75`), which
depends on `size_of::<SourceText>()` = one `Arc` pointer, invariant under adding fields to
`SourceInner`. Adding `filename: Option<String>` and `line_ends: OnceLock<Vec<i64>>` to `SourceInner`
does not change `size_of::<SourceText>()`. The `lib.rs` floor tests (`source_text_probe_above_floor`,
etc.) also remain valid. No defect — recorded so the judge knows this load-bearing safety claim was
checked and holds.

---

## design-7 — efficiency claims (OnceLock line_ends cache, O(1) cp→byte, O(N) residual in Span::text()) verified accurate

Section: §2.6 step 3, §7 item 1, and the codepoint-efficiency exploration.

Verification: Confirmed against source:
- Rust `line_ends` is `OnceLock<Vec<i64>>` on `TerminalSource`, lazily built via
  `chars().enumerate().filter(== '\n')` (`terminalsrc.rs:46`, `191-206`) — matches §2.6.5's "built via
  `text.chars().enumerate()`, **not** `char_indices()`" claim (load-bearing for codepoint columns).
- cp→byte is O(1) by direct index (`terminalsrc.rs:114, 145`); byte→cp is O(log N) `partition_point`
  (`terminalsrc.rs:160`). Matches exploration-codepoint-efficiency §3.
- `Span::text()` is O(end) per call — single `char_indices()` forward pass (`span.rs:286-327`); no
  cp_to_byte table on `SourceInner`. Matches §7's residual claim.
- Python `Span` is frozen + slots carrying raw `str` (`terminalsrc.py:48-55`), so the §7-item-1 claim
  that Python `Span.line_col()` must recompute O(N) per call (no reachable cache) is accurate; the
  `TODO(py-span-linecol-cache)` follow-up is genuine.

No defect. Recorded as confirmed so these are not re-questioned downstream.

---

## design-8 — clockwork formatter anatomy, placement rationale (`errors.py` already taken), and the `get_span` sourceless-fallback removal are accurately grounded

Section: §1.2, §2.10 placement, §2.10 "what clockwork keeps/drops".

Verification: Confirmed:
- `format_line_with_error` (`~/tps/clockwork/clockwork/dsl/ir/cst_util.py:70-92`) matches the design's
  quoted anatomy exactly, including the 1-based header / 0-based caret split (cst_util.py:89-91) and the
  `get_span(line_col.line_span, terminals)` sourceless fallback (cst_util.py:40-48, comment "sourceless
  line_span residual" at line 46).
- `fltk/fegen/pyrt/errors.py` does exist and is the `ErrorTracker`/`ParseContext`/`TokenType` machinery
  (errors.py:1-20+), so §2.10's rationale for a *new* `error_formatter.py` module (rather than
  overloading `errors.py`) is sound and grounded.
- The caret-less parse-error path (`parse.py:56-61` — actually `parse.py:59-61` in the consumer) works
  from `error_position()` (a raw int), not a span; §2.10 / §6-Q4 correctly scope it out.

One small precision note (not a defect): the design quotes `parse.py:56-61`; the actual lines are
`parse.py:59-61` (the `error_linecol = terminals.pos_to_line_col(backend.error_position())` block).
Off-by-a-few line cite; content is correct.

No defect on substance.

---

## design-9 — the "regen IS required (Python parsers)" claim is correct and the gsm2parser change site is accurately located

Section: §2.8 "Generated parser threading (Python)", §4.6, §5, §7.

Verification: Confirmed. `gsm2parser.py:105-118` builds `_source_text` via
`iir.Construct.make(self.SourceTextType, text=FieldAccess("terminals", VarByName("terminalsrc", …)))`,
emitting `SourceText(text=terminalsrc.terminals)` (generated output confirmed at
`fltk/fegen/fltk_parser.py:16`). Adding a second kwarg `filename=terminalsrc.filename` does change this
construction expression, so regen of the Python parsers IS required — the design's honesty here
(contrasting the prior draft's "no regen") is correct.

Caveat worth flagging: the generated line uses `fltk.fegen.pyrt.span.SourceText` (the **backend
selector**, `fltk/fegen/pyrt/span.py`), which resolves to the **Rust** `SourceText` when `fltk._native`
is importable. So the regenerated `SourceText(text=…, filename=…)` will, at runtime under the Rust
extension, call the *Rust* pyo3 `SourceText.__new__` with a `filename` kwarg. This is fine *iff* the
Rust `SourceText::new` gains the `filename=None` param (which §2.8's Rust table does include) — but it
means the §2.8 Python-regen change and the Rust `SourceText::new` signature change are **coupled**: ship
one without the other and the generated Python parser raises `TypeError: unexpected keyword argument
'filename'` whenever it runs against the Rust backend. The design lists both changes but does not call
out that they must land together; an implementer treating "Python regen" and "Rust ctor param" as
independently-mergeable steps can break the Python-parser/Rust-SourceText combination.

Consequence: Partial/interleaved implementation (Python regen merged before the Rust `SourceText::new`
filename param) breaks every run of a generated Python parser under the Rust span backend. Worth an
explicit "these two changes are atomic" note.

---

## Summary of load-bearing verifications

Confirmed accurate: crate dependency edges (`fltk-native → fltk-cst-core`, `fltk-parser-core →
fltk-cst-core`, `fltk-cst-core →` none; `crates/fltk-parser-core/Cargo.toml:16`,
`Cargo.toml:23-25`), so the move-down (Option 1) is dependency-legal and cycle-free as claimed (§2.5,
§7); `LineColPos`/bisect current location (`terminalsrc.rs:18-23`, `180-228`) and re-export
(`lib.rs:27`); the `SourceInner` "room for cached metadata" comment (`span.rs:44-45`); ABI-probe
invariance (design-6); efficiency claims (design-7); clockwork formatter anatomy (design-8); Python
regen necessity (design-9).

Primary risks: design-1 (Rust-parser spans get no filename — the headline feature is unmet on the Rust
backend / the §4.1 cross-backend filename test is unimplementable as written) and the coupled
design-9 caveat (Python regen + Rust `SourceText::new` filename param must land atomically). design-2/3
are consequences/edge-divergences that will surface during TDD; design-4/5 are compile-correctness gaps
in the stated mechanism.
