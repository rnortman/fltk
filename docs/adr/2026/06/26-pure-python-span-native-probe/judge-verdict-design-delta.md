# Judge verdict — design (delta) review

Phase: design (delta). Doc: `design-delta-python-rust-isolation.md` (amends `design.md`).
Base 49e9701..HEAD e0e0157. Round 1.
Notes: 1 reviewer file (`notes-design-delta-design-reviewer.md`); 4 findings, all dispositioned Fixed.
Authoritative user directive: `notes-design-user-2.md`. D8.1 is a deliberate open user-judgment item (per orchestrator) — not adjudicated as a disputed finding.

The delta design was authored with the disposition fixes baked in (committed `d8e3760`); the committed doc IS the post-fix state. Each fix verified present in the doc AND source-backed against ground truth.

## Other findings walk

### design-1 — Fixed
Claim: D3.1's "verified by pyright: `fltk._native.Span` values are assignable to `SpanProtocol`" is false and contradicts D5.2/D4; consequence is an internal contradiction in the load-bearing justification that would mislead an implementer into writing a native-side static-assignability assertion that cannot pass.
Source-back: `span_protocol.py:6,67-79` types `line_col`/`line_col_or_raise` with `terminalsrc.LineColPos`; `_native/__init__.pyi:14,67-68,75` returns the *native* `LineColPos` (distinct nominal class). Method-return covariance fails → native is NOT statically a `SpanProtocol`. Reviewer's pyright probe and the responder's reading both correct.
Doc inspection: current D3.1 (delta §D3.1) now reads "with this, **`terminalsrc.Span` values** are assignable … **Native `fltk._native.Span` is *not* statically assignable**" citing the `LineColPos` nominal gap, with native conforming by `.pyi` declaration + runtime `isinstance` per D5.2 and the residual gap tracked as `TODO(spanprotocol-native-linecol)`. Lead-in softened to "satisfied by both backends *at runtime* (and statically by `terminalsrc.Span`)". D4 ("both runtime backends satisfy") and D5.2 are now mutually consistent; no remaining prose asserts static native conformance.
Assessment: the false half is retracted exactly as the finding requested; the corrected statement matches ground truth and removes the contradiction. Accept.

### design-2 — Fixed
Claim: D3.2's `SourceText` repoint omits the second registration at `gsm2parser.py:78-84`; consequence is `ValueError("Conflicting type registration")` at `ParserGenerator.__init__`, crashing all Python-parser generation before the D6 regen can run (hard blocker).
Source-back: `SourceText` (cname="SourceText") is registered at `context.py:125-132` (module=`span`) AND re-registered at `gsm2parser.py:78-84` (module=`span`). Same `TypeKey`; `TypeRegistry.register_type` (`context.py:19-25`) raises when an existing key gets a differing `TypeInfo`. Repointing only `context.py`→`terminalsrc` leaves the two `TypeInfo`s differing → raise. Confirmed `gsm2parser.py:120-127` is a *construction* expression (emits `terminalsrc.SourceText(...)`), not a third registration — exactly two registration sites exist, so naming both is complete.
Doc inspection: current D3.2 calls out "**TWO sites — both must move together**", names `context.py:125-132` and `gsm2parser.py:78-84`, documents the `ValueError` and the `genparser.py:83` ordering, and offers move-both-or-delete.
Assessment: fix addresses the blocker at the named lines and is complete (no missed third site). Accept.

### design-3 — Fixed
Claim: D6 only gestures at "tests that assert the old surface" without enumerating the prior-work suites that pin the `terminalsrc.Span | fltk._native.Span` union; several are pyright-gated by `make check`. Consequence: post-implementation `make check`/pytest fail on pre-existing tests the design never named, with no retarget/delete contract → implementer stuck or silently drops coverage.
Source-back: `tests/test_gsm2tree_rs.py:1152-1156` (`test_imports_span_module`, `test_imports_fltk_native`) and `:1220-1222` (`test_span_annotation_exact_protocol_union` asserting the union string) exist as claimed; `fltk/fegen/test_cst_protocol.py:487` ("§4 item 8 — additive-widening") with `:536` `get_native_span(...) -> fltk._native.Span` and the three named functions (`:543,:558,:592`) exist. Pyright scope `include = ["fltk", "*.py"]` (`pyproject.toml:50`) → `fltk/fegen/test_cst_protocol.py` is gated, `tests/` is pytest-only. All grounded.
Doc inspection: current D6 adds "Pre-existing union-surface tests must be retargeted", enumerates each suite by file:line and gives an explicit disposition contract (retarget the `test_gsm2tree_rs` `.pyi` assertions to `SpanProtocol` + dropped imports; rework-or-retire the `test_cst_protocol` union-widening suite, implementer's stated choice).
Assessment: every named suite is real and in the stated scope; the fix supplies the missing disposition contract. Accept.

### design-4 — Fixed (input to D8.1, not a defect)
Claim: R2's repo-wide "pyright identical with/without `_native`" clause is met for the generated pipeline but NOT repo-wide under the keep-both default, because `span.py:8-14` and `span_protocol.py:89-94` (`AnySpan`) remain stub-sensitive inside `make check` pyright scope. Reviewer explicitly framed this as "input to D8.1, not a defect."
Source-back: `span_protocol.py:89-94` defines `AnySpan = _pymod.Span | _RustSpan` (try) ↔ `_pymod.Span` (except) — stub-sensitive, under `fltk/`. Pipeline-stub-stability (D5.1) holds because generated modules name neither `fltk._native` nor `span`. Confirmed.
Doc inspection: current D8.1 now distinguishes the pipeline-scoped reading (satisfied under keep-both) from the broader repo-wide R2 clause (not met under keep-both, requires retiring the selector concept), keeping the default and leaving the decision to the user.
Assessment: the enrichment surfaces the tradeoff with R2's scope explicit without resolving it; appropriate disposition. Per orchestrator instruction, D8.1 is a deliberate open user-judgment item, not a REWORK trigger. Accept.

## Approved

4 findings: 4 Fixed verified (design-1 contradiction retracted and source-consistent; design-2 blocker fully named, no missed registration site; design-3 named suites all real and scope-correct with disposition contracts supplied; design-4 R2-scope enrichment appropriate, D8.1 left open by design).

No disputed items.

---

## Verdict: APPROVED

All four dispositions acceptable; every fix is present in the committed delta and source-backed against ground truth (`span_protocol.py`, `_native/__init__.pyi`, `iir/context.py`, `gsm2parser.py`, the named test suites, `pyproject.toml` pyright scope). The design is internally consistent (D3.1/D4/D5.2 no longer contradict). D8.1 remains a deliberate open user-judgment question, not a defect.
