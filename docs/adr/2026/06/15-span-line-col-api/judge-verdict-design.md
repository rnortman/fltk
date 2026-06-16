# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/06/15-span-line-col-api/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 7 findings.

Design phase → no Added-TODOs walk (code-phase concept). The only TODO in scope is a
*proposed* future `TODO(linecol-dedup)`, adjudicated under design-5 below (its `TODO.md`
pairing requirement), not under the added-TODO rubric.

All seven findings fact-checked against fltk source on branch `span-line-col-api` and the
clockwork consumer. The two correctness-relevant findings (design-1, design-3) were verified
by reading the actual registration and algorithm code.

## Other findings walk

### design-1 — Fixed
Claim: the new `LineColPos` pyclass is added to `fltk-cst-core/src/span.rs` and the pyi stub,
but the design never accounts for the registration path; without it `fltk._native.LineColPos`
is not importable. Consequence: an implementer following §2.5/§2.6 literally ships a pyclass
that compiles but is unreachable; the pyi stub and any `from fltk._native import LineColPos`
test fail.
Source check: `src/lib.rs:14-15` registers only `m.add_class::<Span>()` / `m.add_class::<SourceText>()`;
`src/span.rs:1-2` re-exports only `{SourceText, Span}`; `fltk-cst-core/src/lib.rs` exports
`span::{SourceText, Span, SpanError}` — no `LineColPos`. The omission is real and load-bearing.
Disposition: §2.5 item 1 now carries a "Registration path (required)" sub-block naming the
three concrete edits (export from `fltk-cst-core/src/lib.rs`, re-export through `src/span.rs:1-2`,
`m.add_class::<LineColPos>()` in `src/lib.rs:14-15`) plus the failure mode.
Assessment: fix addresses the consequence; the three named edits are exactly the missing
registration steps verified above. Accept.

### design-2 — Fixed
Claim: the `+1`/0-based citation is under-specified — clockwork has TWO consumption sites with
different arithmetic; `cst_util.py:89` adds `+1` to line and col (header only), `cst_util.py:91`
uses raw 0-based `col` (caret). Consequence: an implementer who "fixes" col to 1-based to match
the header silently shifts every caret one column.
Source check: `format_line_with_error` (cst_util.py) does `:{line_col.line + 1}:{line_col.col + 1}:`
on the header and `{' ' * line_col.col}^` on the caret — two sites, exactly as claimed; the
caret is the strict 0-based consumer.
Disposition: §2.1 bullet rewritten to name both sites and flag the caret as the strict 0-based
consumer. Conclusion (keep 0-based) unchanged; this is a groundedness improvement.
Assessment: accurate anchoring fix. Accept.

### design-3 — Fixed (load-bearing correctness finding)
Claim: §2.1/§3 imply the `start<0 → None` behavior is "a property of the inherited algorithm,"
but the ported `pos_to_line_col` treats `pos = -1` as in-domain and returns
`LineColPos(line=0, col=-1)` — so `None`-on-`start<0` is a NEW guard the span wrapper imposes.
Consequence: an implementer told to "port faithfully" gets `start=-1 → LineColPos(line=0, col=-1)`,
directly contradicting the §3 table's `Span(-1,-1) → None`; the guard must precede the ported
bisect.
Source check — confirmed on BOTH backends:
- Rust `pos_to_line_col` (`terminalsrc.rs`): `if pos < -1 || pos > len { return None }` — rejects
  only `pos < -1`, so `pos = -1` is in-domain. Tests `pos_to_line_col_sentinel_minus_one` and
  `pos_to_line_col_empty_input` both assert `col == -1` for `pos = -1`.
- Python `pos_to_line_col` (`terminalsrc.py:183-205`): raises only on `pos > len`, clamps
  `pos == len`, has NO `pos < 0` guard — `pos = -1` flows through the bisect to `col = -1`.
The reviewer's correctness fork is exactly right.
Disposition: reconciled across six sites — §2.1 both bullets (guard runs *before* the ported
bisect, ordering called load-bearing), §2.4 (Python guard in the `Span` wrapper, not the shared
helper), §2.5 item 2 (Rust `line_col_inner` applies `start<0` up front), §3 table row annotated
"wrapper guard, *not* the ported bisect," and §4.3 a deliberate-divergence unit test pinning
`Span(-1,-1).line_col() == None` against `pos_to_line_col(-1) == LineColPos(line=0, col=-1)`.
Assessment: the disposition correctly identifies this as a real fork, applies the guard before
the bisect on both backends, and test-pins the intentional divergence. Fix is complete and
matches the verified source behavior. Accept.

### design-4 — Fixed
Claim: `terminalsrc.rs:496-502` is cited in §2.1/§3 as "the existing implementation" but it is a
`#[cfg(test)]` assertion; the `col=-1` for empty source actually comes from the end-of-input
clamp, which should be the anchor. Consequence: low — behavior is real and test-backed, but
citing the test as the implementation weakens groundedness.
Source check: `pos_to_line_col_empty_input` is a `#[cfg(test)]` test; the `pos == len → pos - 1`
clamp at `terminalsrc.rs:185-186` (Python `terminalsrc.py:187-188`) is the real source of the
`-1` on empty input. Reviewer is correct.
Disposition: §3 empty-source note re-anchored to the clamp as the implementation source and
demoted `:496-502` to its true role as the cross-backend `#[cfg(test)]` pin; §6.2 tightened.
Assessment: correct re-anchoring. Accept.

### design-5 — Fixed
Claim: Compromise #1 is real and correctly characterized, but the proposed `TODO(linecol-dedup)`
code comment is unaccompanied by the required `TODO.md` entry per CLAUDE.md's two-part TODO
protocol. Consequence: landing the comment alone violates the invariant and fails the burndown
ground-truth audit.
Source check: `grep linecol-dedup TODO.md` → not present. The duplication itself is real:
`fltk._native` links only `fltk-cst-core`, while `pos_to_line_col`/`LineColPos` live in
`fltk-parser-core`, and `parser-core` already depends on `cst-core` (so moving down, not up,
is the only acyclic option). CLAUDE.md "TODO System" does mandate both a `TODO.md` row and a
`TODO(slug)` comment.
Disposition: §7.1 now states the `TODO(linecol-dedup)` comment requires a paired `TODO.md` entry
with the matching slug, describing the move-down refactor and naming the location.
Assessment: mechanical but real; fix makes the paired entry an explicit design deliverable.
Note: this is a *design-time mitigation plan* for a future TODO, not an added TODO in this phase
— so the added-TODO acceptability rubric does not bind here. The dedup work itself is a genuine
design-cycle refactor (cross-crate API move), correctly deferred. Accept.

### design-6 — Fixed
Claim: the ABI "no marker bump" reasoning is sound, but the design omits that `SourceInner` is
shared with `fltk-parser-core::TerminalSource` (which already carries its own `line_ends`), so
adding `line_ends` to `SourceInner` creates a second independent cache over the same text.
Consequence: not a correctness bug (both derive deterministically from immutable `text`), but
duplicated state on the parser hot path's shared allocation that the design did not acknowledge.
Source check: `SourceInner` is `{ text: String }` (`span.rs:46-48`) with a doc comment that
literally says it "leaves room for future cached metadata (e.g. line-offset tables)";
`TerminalSource` holds `line_ends: OnceLock<Vec<i64>>` (`terminalsrc.rs:46`) and is built over a
`SourceText` whose `inner: Arc<SourceInner>`. The two-cache observation is accurate.
The ABI reasoning also checks out: `SourceText` is `{ inner: Arc<SourceInner> }` (`span.rs:56-58`),
`Arc<T>` is one pointer regardless of `T`, and the probe measures the `SourceText` layout
(`span_abi_layout_probe` / `source_text_abi_layout_probe` in `span.rs`), so no marker bump.
Disposition: §2.5 item 3 now carries a "Shared-allocation nuance" paragraph stating the two
independently-populated tables, accepting it given immutability, and noting future consolidation
is entangled with `linecol-dedup`.
Assessment: the design now surfaces the duplicated state as a conscious decision. Accept.

### design-7 — Won't-Do
Claim: the runtime-checkable protocol-extension breakage is real and correctly disclosed; the
finding explicitly states "Nothing factually wrong" and "No structural objection." It raises one
"not surfaced" item: `tests/test_span_protocol.py:103-108` (`TestProtocolHasNoStartEnd`) only
asserts absence of `start`/`end`, and the §4.2 plan to extend it with `callable(SpanProtocol.line_col)`
is "appropriate." Recorded as confirmation, not a defect.
Consequence stated by reviewer: "None beyond the disclosed protocol-extension breakage, which is
inherent and per CLAUDE.md is an acceptable additive consequence."
Disposition rationale: no design change; the finding requests none, the disclosed breakage is
inherent and already documented in §3 and §5, and the single "omission" it names is already in
the §4.2 test plan (verified present).
Adjudication: a Won't-Do must argue the finding does not warrant action. Here the reviewer itself
states there is no defect and no fix needed — the finding is explicitly a confirmation. The one
flagged "omission" (assert the new methods are present on the protocol) is already covered by §4.2,
which adds `callable(SpanProtocol.line_col)` / `callable(SpanProtocol.line_col_or_raise)` to
`TestProtocolHasNoStartEnd` — confirmed present in the design doc. There is no stated consequence
requiring action and no source-grounded gap to close. Per the deweight rule, a finding the
reviewer itself characterizes as "no fix needed" with no actionable consequence → responder wins.
Accept Won't-Do.

## Disputed items

None.

## Approved

7 findings: 6 Fixed verified (design-1 registration path, design-2 two-site 0-based anchoring,
design-3 the load-bearing `start<0` guard fork — guard-before-bisect on both backends and
test-pinned, design-4 clamp re-anchor with the test demoted, design-5 paired `TODO.md` entry for
the future `linecol-dedup`, design-6 shared-`SourceInner` nuance), 1 Won't-Do sound (design-7,
confirmation-only finding with no actionable consequence).

No scope over-reach: the design correctly defers `AnyLineColPos`/`LineColPosProtocol` and
`end_line_col()` to open questions, reuses `LineColPos` rather than inventing a type, and the
`linecol-dedup` cross-crate move is a genuine design-cycle item correctly left as a recommended
TODO with its required `TODO.md` pairing rather than smuggled into this change.

---

## Verdict: APPROVED

All seven dispositions acceptable. The six Fixed edits are present in the design doc and each
matches the verified source behavior — most importantly design-3, where the `pos_to_line_col`
in-domain treatment of `pos = -1` (confirmed on both backends) makes the `start<0 → None` guard
a genuine new fork that the disposition correctly applies before the ported bisect and pins with
a deliberate-divergence test. design-7's Won't-Do is sound: the reviewer raised no defect and the
one item it flagged is already in the §4.2 test plan.
