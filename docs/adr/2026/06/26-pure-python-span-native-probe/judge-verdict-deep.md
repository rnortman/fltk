# Judge verdict — deep review

Phase: deep. Base `49e9701`..HEAD `9ca3707` (responder fixes committed on top of reviewed `ab38ec7`). Round 1.
Notes: 7 reviewer files (error-handling, correctness, security, test, reuse, quality, efficiency); 13 dispositioned items.
Native (`fltk._native`) is built in this environment, so the native-present paths actually exercise.

## Added TODOs walk

### errhandling-1 — TODO(span-selector-broken-native-diagnostic) at span.py:8
Q1 (worth doing): yes — `except Exception` swallows a present-but-broken native extension (ABI/OSError/SystemError), degrading `span.Span` to the pure-Python type with no signal; surfacing that is worth doing.
Q2 (design/owner input required): yes — the fix is a genuine behavioral tradeoff in a user-sensitive area: narrow to `except ImportError` (must stay correct for the pure-Python namespace-package case, which raises `ImportError` for the missing `Span`) vs. log-and-fallback (re-adds a diagnostic the user explicitly asked removed for the *absent* case). Robustness-vs-diagnosability is a product call, not a mechanical edit. The `AnySpan` block in `span_protocol.py` must move in lockstep.
Furthermore (iteration-worsened check): this diff removed the `warnings.warn` that previously fired on the broken-native path, so the broken-native diagnostic was worsened. But (a) the over-broad `except Exception` itself is pre-existing (reviewer states it "was present before this diff and is unchanged"); (b) the warning removal was the explicit user-directed goal of the change, not an incidental responder regression; (c) `span.py` is now out of the generated pipeline, so impact is confined to the standalone selector utility, and the consequence is rare and non-corrupting. The TODO is well-formed (TODO.md entry + `TODO(slug)` comment at the exact site + the gating lockstep note), so it is surfaced, not silently deferred.
Assessment: Q1 yes, Q2 yes; the worsening is user-directed and the issue is recorded with visibility. TODO acceptable.

### reuse-2 — TODO(unparser-source-helper) at test_is_span_guard.py:62
Q1 (worth doing): yes — `_generate_unparser_source` re-implements `plumbing.generate_unparser`'s 7-step assembly (called 4x in the file) because plumbing exposes no pre-`exec` source hook; real drift risk on any assembly-list change.
Q2 (design/owner input required): yes — the clean fix is a *production-library* API addition (`plumbing.generate_unparser_source`, with `generate_unparser` exec'ing its output), an API-shape decision that ripples through both assembly sites (`generate_unparser` and `genunparser.py`); out of scope for a respond-mode test-helper patch. Severity is low (test-only duplication), so deferring a production API refactor to fix a fixture dedup is proportionate.
Assessment: Q1 yes, Q2 yes. TODO acceptable.

### test-3 — TODO(spanprotocol-native-linecol) at span_protocol.py:87 (augmented)
Q1 (worth doing): yes — the underlying `spanprotocol-native-linecol` slug (unify `LineColPos` across backends so native spans statically conform to `SpanProtocol`) is a real, recorded cross-backend gap. The test-3 augmentation adds a *constraint*: any future fix that makes `SpanProtocol`'s structural surface native-dependent must add a stub-stability guard for the generated pipeline. Worth recording — that constraint is the exact future change that would reopen the R2 hole.
Q2 (design/owner input required): yes — the linecol unification is a cross-backend (Python module + Rust `.pyi`) design change. The guard the reviewer wants (a differential stub-present-vs-absent pyright run) is non-trivial infra: the design's own D6 named it the central R2 test, the implementer deviated (increment 18) to source-level checks for stated reasons (toggling the committed stub mid-test is awkward; no suite precedent), and a clean runtime structural guard is hard because the `AnySpan` block legitimately names native *in the same module*, so a naive "span_protocol names no native" check would false-fail.
Crucially — no current defect: the correctness reviewer empirically re-checked the generated triad with `fltk/_native/__init__.pyi` removed and got 0 errors, stable. The blind spot is conditional on a *future* change that has its own tracked slug, and the constraint is bound at the right location (`span_protocol.py`, where the dangerous edit would be made), so whoever edits `SpanProtocol`'s surface sees it.
Assessment: weakest of the three but defensible — no current defect, the proportionate fix is the linecol design change itself, and the residual risk is gated and surfaced at the dangerous site. TODO acceptable. (This is *not* an iteration-created defect; HEAD's pipeline is stub-stable.)

## Other findings walk

### correctness (whole review) — No findings
Reviewer traced registry split (collision-free), registry-independent construction, `is_span` dual-backend guard, clean hybrid removal, and ran empirical end-to-end + pyright-stub checks. Disposition verified the traces against source. Nothing to action. Accept.

### security (whole review) — No findings
Change is annotation/isolation plumbing; it *removes* an `importlib.import_module` ACE sink (`_load_rust_cst_classes`); no new trust-boundary crossing. Net surface reduction. Accept.

### test-1 — Fixed
Claim: no combined native-present unparse round-trip test; the §2.6 regression (probe-bound `is_span` rejecting `terminalsrc.Span` → `ValueError("Unparsing failed")`) is unpinned; properties were split across files with no native-present coupling.
Evidence: `tests/test_python_parser_span_backend.py::test_native_present_unparse_round_trip` added — skips unless `fltk._native` importable, generates parser+unparser, parses "hello", asserts `type(cst.span) is terminalsrc.Span`, then `unparse_cst`→`render_doc == "hello"` — all three properties in one native-present test. Ran it here with native built: PASSED (exercises the bug-triggering condition, not a trivial native-absent pass).
Assessment: fix addresses the consequence at the named gap and is genuinely exercised. Accept.

### test-2 — Fixed
Claim: source-level "no native / no selector" assertions covered only the `fltk_cst` pair; the other 4 committed pairs (bootstrap, regex, toy, unparsefmt) silently unasserted.
Evidence: both tests parameterized over `ALL_PROTOCOL_MODULES` / `ALL_CONCRETE_CST_MODULES` (5 pairs each). Verified by `ls` that these are *all* committed `_cst.py`/`_cst_protocol.py` pairs (no unenumerated pair). Ran: 10 parametrized cases PASSED.
Assessment: coverage now matches the claim. Accept.

### test-4 — Fixed
Claim: concrete-CST check was import-line-only; a lazy-string `fltk._native.Span` annotation (no import line, under `from __future__ import annotations`) would slip past it while failing pyright.
Evidence: check strengthened to context-bounded — every line containing `fltk._native` must be the runtime `sys.modules.get("fltk._native")` lookup, else fail; comment added explaining the principled asymmetry with the protocol check. Ran: PASSED for all 5 concrete modules.
Assessment: closes the lazy-string blind spot at the pytest level. Accept.

### quality-1 — Fixed
Claim: `_source_text_init`'s module `VarByName` (names `terminalsrc` MODULE) was typed `typ=self.SourceTextType` (the class), misrepresenting the denotation and establishing a third constructor-call idiom.
Evidence: `gsm2parser.py:146` changed to `typ=iir.Type.make(cname="module")`, matching the 5-site module-VarByName convention; explanatory comment added. Disposition reports `make gencode` output byte-identical (output was already correct per correctness reviewer); `make check` green per dispositions header.
Assessment: removes the divergent pattern at zero output cost. Accept.

### reuse-1 — Won't-Do
Claim: `_make_word_grammar` duplicates `_make_regex_grammar`; consequence is dual-update drift on a `gsm` API change.
Rationale: the reviewer's own remedy (call the other file's `_`-prefixed helper) couples test modules to another file's private API and breaks per-module self-containment; a new shared util module is disproportionate for two ~15-line fixtures. The drift risk is shared by dozens of suite fixtures, not specific to this pair.
Assessment: nit; rationale argues active harm (loss of test isolation) from the proposed fix. Accept.

### quality-2 — Won't-Do
Claim: protocol check uses broad full-text `"fltk._native" not in text`; reviewer wants it narrowed to a line-level import check for symmetry with the CST check.
Rationale: narrowing would WEAKEN the check and reintroduce the exact lazy-string blind spot test-4 closes. Protocol modules legitimately contain ZERO `fltk._native` references (grep count 0 across all 5), so full-text "appears nowhere" is both correct and strictest; the asymmetry with the CST check (one known runtime `sys.modules.get`) is principled and now commented. The false-positive scenario (hand-added comment naming native) cannot occur in machine-generated output.
Assessment: strong Won't-Do — the suggested change is actively harmful and contradicts the same-reviewer-set test-4 fix; responder correctly kept protocol strict while strengthening CST. Accept.

### quality-3 — Won't-Do
Claim: three codegen sites emit `from __future__ import annotations` via divergent idioms (pygen text helper vs raw AST; one omits `asname=None`).
Rationale: stylistic-only across genuinely distinct generation layers (committed-file pygen-land vs two in-memory raw-AST paths); `asname=None` vs omitted is behaviorally identical (AST default); a shared helper would have to bridge the pygen/raw-AST boundary among three independent entry points for zero behavioral benefit; the statement is stable with no realistic churn.
Assessment: cosmetic nit, no correctness consequence; rationale adequate. Accept.

### efficiency-1 — Won't-Do
Claim: `is_span` re-resolves the native span type (`sys.modules.get`+`getattr`+`isinstance`) per non-`terminalsrc.Span` child during unparse.
Rationale: reviewer's own measurement — sub-microsecond per child, dominated by Doc construction/rendering, "a minor regression, not a scale ceiling," explicitly "optional." Current form matches the blessed lazy `_get_native_span_type()` pattern; memoizing adds cache-correctness subtlety (cache only successful resolution) for negligible saving. Not a design-committed hot path.
Assessment: nit the reviewer marked optional; consistency with the established pattern outweighs the micro-optimization. Accept.

## Approved

13 dispositioned items: 4 Fixed verified (test-1, test-2, test-4, quality-1), 4 Won't-Do sound (reuse-1, quality-2, quality-3, efficiency-1), 3 TODOs acceptable (span-selector-broken-native-diagnostic, unparser-source-helper, spanprotocol-native-linecol), 2 No-findings reviews (correctness, security) verified.

No disputed items.

---

## Verdict: APPROVED

All dispositions acceptable. Fixed claims verified against diff and by running the named tests under native-present (the bug-triggering condition). The three TODOs each pass the two-question rubric and carry both a `TODO(slug)` comment and a TODO.md entry. The Won't-Do rationales argue active harm or genuine non-consequence (notably quality-2, where the reviewer's suggested narrowing would have reopened the test-4 blind spot). No current defect was deferred: the one iteration-worsened item (errhandling-1's lost warning) is user-directed, confined to an out-of-pipeline utility, and visibly recorded; test-3's risk is conditional on a tracked future change and the pipeline is empirically stub-stable at HEAD.
