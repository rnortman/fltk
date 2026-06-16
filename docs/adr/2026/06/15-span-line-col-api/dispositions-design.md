# Dispositions: design review of `line_col()` on `SpanProtocol`

Round 1. Reviewer notes: `notes-design-design-reviewer.md`. Design: `design.md`.

All seven findings were fact-checked against fltk source (branch `span-line-col-api`),
the clockwork consumer, and `TODO.md` before disposition. The two correctness-relevant
findings (design-1, design-3) were verified by reading the actual registration and
algorithm code.

---

design-1:
- Disposition: Fixed
- Action: §2.5 item 1 ("A `LineColPos` pyclass") — added a "Registration path (required)"
  sub-block listing the three concrete edits needed for `fltk._native.LineColPos` to be
  importable: (a) export from `fltk-cst-core/src/lib.rs:18`, (b) re-export through the
  extension shim `src/span.rs:1-2`, (c) `m.add_class::<LineColPos>()?` in `src/lib.rs:14-15`,
  plus a sentence on the failure mode (the type compiles but is unreachable).
- Severity assessment: Verified accurate — `src/lib.rs:14-15` registers only `Span`/`SourceText`,
  `src/span.rs:1-2` re-exports only `{SourceText, Span}`, and `fltk-cst-core/src/lib.rs:18`
  exports `span::{SourceText, Span, SpanError}`. Without these steps an implementer following the
  design literally ships a pyclass that compiles but cannot be imported or `isinstance`-checked,
  and the §2.6 pyi stub and any `from fltk._native import LineColPos` test would fail. A real,
  load-bearing omission in the "additive surface" plan.

design-2:
- Disposition: Fixed
- Action: §2.1 "0- vs 1-based" bullet — rewrote to name **both** clockwork consumption sites:
  the header `cst_util.py:89` (adds `+1` to line and col) and the caret-indent line
  `cst_util.py:91` (raw 0-based `col`), identifying the caret as the strict 0-based consumer that
  would shift one column if `line_col()` ever went 1-based.
- Severity assessment: Verified accurate — `cst_util.py:89` does `{line+1}:{col+1}` for the header
  only; `cst_util.py:91` does `' ' * line_col.col` (raw). The original single-line citation
  under-specified the blast radius; the conclusion (keep 0-based) was already correct, so this is
  a groundedness/anchoring improvement, not a behavior change.

design-3:
- Disposition: Fixed
- Action: This is the load-bearing correctness finding. Verified against `terminalsrc.rs:182`
  (`pos < -1` is the rejection threshold, so `pos == -1` is in-domain and returns
  `LineColPos(line=0, col=-1)`). Reconciled the "exact port" language with the `start<0 → None`
  guard across four sites: §2.1 empty/zero-width bullet (clarified the clamp produces empty-source
  `col=-1`, while the `start=-1 → None` is a *new* guard, not inherited); §2.1 sourceless bullet
  (retitled "guard runs *before* the ported bisect", stated the ordering is load-bearing); §2.4
  (Python — added a paragraph that the guard lives in the `Span` wrapper, not the shared helper,
  and runs first); §2.5 item 2 (Rust — `line_col_inner` must apply `start<0` up front; the ported
  bisect alone would return a real `LineColPos`); §3 table row `Span(-1,-1)` (annotated "wrapper
  guard, *not* the ported bisect"); §4.3 (added a deliberate-divergence unit test pinning
  `Span(-1,-1).line_col() == None` against `pos_to_line_col(-1) == LineColPos(line=0, col=-1)`).
- Severity assessment: Real correctness fork. An implementer told to "port `pos_to_line_col`
  faithfully" would produce `start=-1 → LineColPos(line=0, col=-1)`, directly contradicting the §3
  table's `Span(-1,-1) → None`. The guard must precede the ported bisect or `UnknownSpan.line_col()`
  silently returns a bogus value instead of `None`. The "exact port" framing obscured this; now
  explicit and test-pinned.

design-4:
- Disposition: Fixed
- Action: §3 empty-source note — re-anchored the `col=-1` causal claim to the end-of-input clamp
  (`terminalsrc.py:187-188`, `terminalsrc.rs:185-186`) as the implementation source, and demoted
  `terminalsrc.rs:496-502` to its true role as the cross-backend `#[cfg(test)]` assertion that
  pins it. Also tightened §6.2 to reference the clamp consistently.
- Severity assessment: Low. The asserted behavior is real and test-backed; the original prose cited
  a test as if it were the implementation, weakening groundedness. The clamp is the correct anchor;
  the test now correctly serves as the equivalence pin.

design-5:
- Disposition: Fixed
- Action: §7.1 final mitigation paragraph — added that per the project's two-part TODO protocol
  (CLAUDE.md "TODO System"), the `TODO(linecol-dedup)` code comment requires a paired `TODO.md`
  entry with the matching slug, describing the move-down refactor and naming the location. Verified
  no `linecol-dedup` entry currently exists in `TODO.md`.
- Severity assessment: Mechanical but real. CLAUDE.md mandates both a `TODO.md` row and a
  `TODO(slug)` comment; landing only the comment violates the invariant and fails the repo's
  burndown ground-truth audit. The fix makes the paired entry an explicit design deliverable.

design-6:
- Disposition: Fixed
- Action: §2.5 item 3 ("Line-ends cache on `SourceInner`") — added a "Shared-allocation nuance"
  paragraph stating that `SourceInner` is the same `Arc<SourceInner>` allocation
  `fltk-parser-core::TerminalSource` is built over, that `TerminalSource` already carries its own
  `line_ends` cache (`terminalsrc.rs:46`), and that this change therefore creates a second
  independently-populated table over the same text — accepted given immutability, flagged as a
  conscious decision, with a note that future consolidation is entangled with `linecol-dedup`.
- Severity assessment: Not a correctness bug (both tables derive deterministically from immutable
  `text`), but verified accurate: `TerminalSource` holds `line_ends: OnceLock<Vec<i64>>` at
  `terminalsrc.rs:46` and is built from a `SourceText` whose `inner: Arc<SourceInner>`. The design
  previously framed the cache as isolated to the span backend; it is structurally reachable from
  the parser hot path's shared allocation. Worth one paragraph so the duplicated state is a
  deliberate choice.

design-7:
- Disposition: Won't-Do
- Action: No design change. The finding explicitly states "Nothing factually wrong" and "No
  structural objection" — it is recorded as confirmation that the runtime-checkable
  protocol-extension breakage is real, correctly disclosed (§3 "Protocol `isinstance` breakage",
  §5), and an accepted additive consequence per CLAUDE.md. The one item it flags as "not surfaced"
  (that `tests/test_span_protocol.py:103-108` only asserts absence of `start`/`end`) is already
  covered by the §4.2 plan to extend `TestProtocolHasNoStartEnd` with
  `callable(SpanProtocol.line_col)` assertions, which the finding itself calls "appropriate."
- Severity assessment: None. The finding requests no change; the disclosed breakage is inherent to
  extending any `@runtime_checkable Protocol` and is already documented in two sections. Adding
  further text would restate content already present.
- Rationale (Won't-Do): The reviewer concluded "no fix needed" and raised no defect. The single
  "omission" it names (asserting the new methods are present on the protocol) is already in the
  design's §4.2 test plan (`callable(SpanProtocol.line_col)` /
  `callable(SpanProtocol.line_col_or_raise)`), verified present at `design.md` §4.2. There is no
  source-grounded gap to close, and duplicating the disclosure would add redundancy the
  cleanup-editor pass is meant to remove.
