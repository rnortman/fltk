# Design Review: Phase 1 Span Rust Implementation

Concise. Precise. No padding. Audience: smart human/LLM.

Reviewed `design.md` against `requirements.md`, `exploration.md`, `request.md`, and source
(`fltk/fegen/pyrt/terminalsrc.py`, `src/lib.rs`, `Cargo.toml`, `fltk/unparse/gsm2unparser.py`,
PyO3 0.23.5 macro source in `~/.cargo/registry`).

Verified and correct (not findings):
- PyO3 0.23.5 `#[pyclass(eq)]` derives `__richcmp__` that downcasts `other` to `Self` and returns
  `py.NotImplemented()` on mismatch (`pyo3-macros-backend-0.23.5/src/pyclass.rs` `pyclass_richcmp`).
  Satisfies requirement "equality with non-Span returns NotImplemented" (req line 55) automatically.
- Manual `PartialEq`/`Hash` using only `(start,end)` is honored by the `eq`/`hash` derive — satisfies
  acceptance criteria 4, 5, 13.
- `isinstance(child, Span)` dispatch is real: `gsm2unparser.py:1075,1178` emit `IsInstance(..., Span)`.
  Single-type Option A preserves it. Exploration's cited line (`gsm2unparser.py:983`) is stale but the
  pattern exists.
- `extract_span_text` slicing path confirmed (`gsm2unparser.py:1804`); design leaves it untouched. Correct.
- Source struct (`terminalsrc.py:7-15`) matches exploration exactly.

---

## design-1: `text()` returns `Option<String>` (copy), contradicting the Python memory-efficiency constraint

Section "Rust Implementation Details" → `text` method (design.md:159-177) and the note at design.md:177:
"Returns `Option<String>` ... PyO3 converts `String` to a Python `str`."

Requirement (requirements.md:110): "Retrieving source text from Python ... ideally still uses
non-copying slicing of immutable data rather than allocating new strings per access." The design
allocates a new owned `String` on the Rust side (`to_owned()`) and then PyO3 copies that into a fresh
Python `str` on every `text()` call — two allocations per access, the opposite of non-copying slicing.

The existing Python path (`terminals[span.start:span.end]`) also allocates a new `str` per slice, so
the Rust path is no worse than today, but the design claims memory efficiency as a motivating decision
(struct-layout discussion, `Arc<SourceInner>` rationale) while silently dropping it at the one
user-facing retrieval point. The requirement is "ideally," not mandatory, so this is acceptable — but
the design should explicitly acknowledge the per-access copy and why it is accepted (PyO3 cannot return
a borrow into `Arc` data across the GIL boundary), rather than presenting `Option<String>` as if it
satisfies the efficiency goal.

Consequence: If left unstated, an implementer or reviewer may believe the "better API" delivers
zero-copy text access (the Rust-side constraint requirements.md:109 talks about), and may build later
phases assuming cheap repeated `text()` calls. Repeated `.text()` on large spans is O(n) copy each time.
Suggested fix: add one sentence noting Python-facing `text()` copies (bounded by Python/PyO3 FFI), and
that the zero-copy constraint (req 109) applies to the *Rust-internal* representation only, which the
`Arc<SourceInner>` design does satisfy.

---

## design-2: `char_slice` helper used but never defined

Section "Rust Implementation Details" → `text` method (design.md:173): `char_slice(src, start, end).map(...)`.

The non-ASCII slow path calls `char_slice`, a function that appears nowhere else in the design or in
the codebase (confirmed: only two grep hits, both in design.md). The signature, return type
(`Option<&str>` is implied by `.map(|s| s.to_owned())`), and char-vs-byte semantics are left to the
implementer.

Consequence: The single hardest correctness point in the whole design — converting Python character
indices to Rust byte offsets (requirements.md:107, exploration.md:263) — is delegated to an unspecified
helper. The Unicode test (test plan #16: `SourceText("héllo")` → `Span.with_source(1,4).text() == "éll"`)
is the acceptance gate for exactly this code, and there is no spec for how the conversion handles
end-of-string, a start index past the char count, or `start`/`end` landing mid-... (they are char
indices so cannot land mid-char, but the helper must still bound-check against char count, not byte len).
Suggested fix: specify `char_slice` (walk `char_indices()`, map char index→byte offset, bound-check
against total char count, return `None` when `end` exceeds char count). Note the ASCII fast path's
`end > src.len()` check is in *bytes* and is only valid because for ASCII byte len == char count.

---

## design-3: `Span` is `Clone` and source-bearing, but nothing in Phase 1 ever attaches source on the parse path — "better API" is unreachable from real CSTs this phase

Sections "Python API Surface" (design.md:65-66) and "terminalsrc.py Changes" (design.md:111-119).

The design adds `Span.with_source` and `SourceText`, but the only `Span` construction sites in
production are sourceless: `terminalsrc.py:38,43,60,63` (`Span(pos, ...)`) and ~80 keyword sites in
`fltk_parser.py`. None are modified (out of scope — req lines 20, 24-28: "Generated parser/unparser
changes" out of scope). So after Phase 1, every `Span` in an actual parsed CST has `source=None`, and
`node.span.text()` returns `None` for real parsed nodes. The "better API where span.text() returns
source text directly" (requirements.md:9, request.md:28 user's core concern) is only exercisable by
hand-constructing `Span.with_source(...)` — i.e., only synthetic-node use cases, never the parsed-node
use case the user emphasized.

This is consistent with the stated scope (the requirements only ask that source-bearing spans *can be
constructed*, criteria 11-13), so it is not a scope violation. The risk is that the design presents the
"better API" as solving the user's stated problem ("always access the source text of a CST node") when
Phase 1 alone does not — wiring the parser to emit source-bearing spans is deferred to a later phase and
the design never says so.

Consequence: User may approve believing Phase 1 delivers source-on-parsed-nodes; acceptance tests
(criteria 11-13) pass with only synthetic construction, masking that the headline use case is unwired.
Suggested fix: add an explicit note that Phase 1 delivers the *capability* and the synthetic-node path;
parser emission of source-bearing spans is a named follow-up phase. Confirm with user this matches intent.

---

## design-4: `SourceInner` is `pub(crate)` with private fields but `with_source` reads `source.inner` — verify field visibility

Sections "with_source classmethod" (design.md:146-149: `source.inner.clone()`) and "SourceText Struct"
(design.md:210-213: `inner: Arc<SourceInner>` with no `pub`).

`Span::with_source` accesses `source.inner`. If `Span` and `SourceText` live in the same module
(`src/span.rs`, per design.md:20 and file-changes table design.md:122-127), private-field access is
fine. This holds as written (both in `span.rs`). Flagging only because the design shows `SourceText.inner`
as private and `SourceInner` fields (`text`, `is_ascii`) as private while `text()` reads `inner.text`
and `with_source` reads `source.inner` — all intra-module, all valid, but the design never states the
single-module assumption. If an implementer splits `SourceText` into its own module, it breaks.

Consequence: Low. Compile error caught immediately if module split occurs; no silent failure.
Suggested fix: one line stating `Span`, `SourceText`, `SourceInner` all live in `src/span.rs` so
field access is intra-module.

---

## design-5: Test plan #2 does not actually test the `NotImplemented` requirement

Section "Test Plan" → new test #2 (design.md:269): `Span(1, 2) != "not a span"`.

Requirements.md:55 and error-message section require equality with non-Span to return `NotImplemented`
(not `False`). `Span(1,2) != "not a span"` evaluates to `True` whether `__eq__` returns `False` or
`NotImplemented` (Python falls back to identity, then negates). So this test cannot distinguish the two
and does not verify the requirement. The behavior is in fact correct (design-1 verification above), but
the test as specified does not gate it.

Consequence: Low — behavior is correct via PyO3 derive, but the requirement is nominally untested. If a
future change replaced the `eq` derive with a manual `__eq__` returning `False`, no test would catch the
regression. Suggested fix: test `Span(1,2).__eq__("x") is NotImplemented` directly, or drop the
requirement's NotImplemented clause from the test-coverage claim.

---

## design-6: `LineColPos` still constructs `Span` positionally and is unmodified — verify re-export keeps it working (it does), but `UnknownSpan` typing changes

Section "terminalsrc.py Changes" (design.md:111-119).

`terminalsrc.py:60,63` construct `Span(int, int)` inside `pos_to_line_col`; `LineColPos.line_span: Span`
(terminalsrc.py:22). After re-export, `Span` is the Rust class — positional construction works (`#[new]`
signature `(start, end)`, design.md:135). Verified compatible. Separately, `UnknownSpan: Final = Span(-1,-1)`
(terminalsrc.py:15) is replaced by an import of a `Py<Span>` instance. The current `Final` annotation and
`@dataclass(frozen, slots)` on `LineColPos` embedding a Rust `Span` as a field: `slots=True` dataclass
holding a non-dataclass Rust object as a field is fine (no equality/hash issue since `Span` is hashable).
No finding — confirming the design's claim (design.md:119) is correct.

Consequence: none (verification of a load-bearing compatibility claim that holds).

---

## design-7: Open Question 2 (classmethod vs kwarg constructor) left unresolved — minor scope/consistency note

Section "Open Questions" #2 (design.md:293).

The design body commits to `Span.with_source` classmethod (design.md:66, 144-149) and writes all test
cases against it (test plan #9, #12-16), then reopens the decision in Open Questions. This is a mild
internal inconsistency: the design is otherwise decisive but defers a choice it has already implemented
throughout. Not blocking; requirements explicitly delegate the choice ("design decides", req line 84).

Consequence: Low — implementer has a fully-specified classmethod path; the open question is cosmetic.
Suggested fix: either close the question (classmethod chosen, rationale already given at design.md:293)
or move it to a "decided" note. Avoid leaving an implemented decision flagged as open.

---

Note: keep this style (concise, source-backed, consequence-bearing) in any docs derived from this review.
