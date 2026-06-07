# Judge verdict — deep review, Rust CST native span

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base f8fdb53..HEAD 99e276a. Round 1.
Notes: 7 deep reviewer files + 1 pre-pass scope; 19 dispositioned findings.
Design: `docs/adr/2026/06/06-rust-cst-native-span/design.md`.

## Added TODOs walk

### reuse-3 / quality-5 — TODO(gencode-poc-fltkg) at Makefile:83-88
Q1 (worth doing): yes — the inline `python -c` PoC-grammar regen diverges from the standard `gen-rust-cst` path; preamble changes (header, lint-suppression) would need dual maintenance.
Q2 (design/owner input required): yes — requires authoring a first-class `.fltkg` source for the PoC grammar so `make gencode` drives it through `genparser`; that's a non-mechanical artifact, not a one-line edit.
Both halves of the two-piece system now present: `TODO.md` entry added (lines 48-50), `# TODO(gencode-poc-fltkg)` comment present in `Makefile`. Pre-existing divergence, not introduced this iteration. Low severity.
Assessment: TODO acceptable.

### efficiency-deep-1 / reuse-1 / quality-1 (`source_as_py` retention) — TODO(span-source-as-py-crosscdylib) at span.rs:148
Q1 (worth doing): yes — confirmed real regression. Every span-returning accessor calls `source_full_text_str()` (full-string `String` clone, `span.rs:168`) then rebuilds a fresh `SourceText` via `get_source_text_type(py)?.call1((full_text,))` — two full-source copies per node read, O(N·M) per traversal, defeating the documented `Arc`-sharing design (`span.rs:14-32`).
Q2 (design/owner input required): yes — the O(1) fix needs an `extract_source_text` generator-preamble helper using the same cross-cdylib `downcast_unchecked` + shared-rlib unsafe invariant as `extract_span`; that is unsafe-Rust design work with a soundness argument, not a mechanical change.
This iteration introduced the regression. Rubric bar: a problem this iteration created cannot be *silently* deferred — must be fixed or surfaced for visibility. Here it is surfaced: full `TODO.md` entry (lines 52-54) describing the O(N·M) cost and fix path, plus a `TODO(span-source-as-py-crosscdylib)` doc-comment cross-reference at `span.rs:148`, and `source_as_py` retained as the correct O(1) primitive for the fix. Visible deferral with design rationale, not silent. Performance regression, not correctness/safety.
Assessment: TODO acceptable.

### quality-4 — TODO(span-make-span-expr-registry) at gsm2parser.py:262
Q1 (worth doing): marginal — `_make_span_expr` hardcodes `VarByName(name="fltk.fegen.pyrt.span.Span")`, a stringly-typed dotted path. The path is stable; a future module rename needs a manual edit. Cosmetic quality, no correctness/safety stake.
Q2 (design/owner input required): **no** — the fix is mechanical and single-file: derive the qualified name from the already-registered `self.TerminalSpanType` in the type registry, or hoist a `_SPAN_CLASS_EXPR` class constant. Within respond's scope; no design cycle, no owner input. Verified: `self.TerminalSpanType` is the registered type already passed as `typ=` to the same `VarByName` (`gsm2parser.py:262-266`).
Rubric outcome: clear NO to Q2 → **do it now**, not defer.
Furthermore — TODO does not actually exist: `span-make-span-expr-registry` appears **only** in `dispositions-deep.md:150`. No `TODO.md` entry (the disposition's own Action text concedes "Not added to TODO.md in this round"), and no `TODO(span-make-span-expr-registry)` comment in code (grep-confirmed, zero hits outside the dispositions doc). CLAUDE.md requires both pieces; neither exists. This is a phantom TODO — the disposition claims a defer it never recorded.
Assessment: disposition wrong on two counts — (1) rubric says do-now, not defer; (2) even as a defer it was never created. REWORK.

## Other findings walk

### correctness-1 — Fixed
Claim: Rust `Span.text()`/`text_str()` sliced source by **byte** offsets while parser-produced `start`/`end` are **codepoint** indices; introduced regression silently corrupting identifier/literal/regex text for any non-ASCII source under the Rust backend (`'héllo'[1:4]` codepoint = `'éll'` vs byte = `'él'`).
Diff at `span.rs:218-248` (`text`) and `:254-295` (`text_or_raise`): both now translate codepoint→byte via `src.char_indices().nth(idx)`, with `end == char_count → src.len()` and empty-string edge cases handled. `text_str` removed (was dead + same bug). Doc comments at `:59-71` now state codepoint semantics. Regression test `test_rust_backend_node_span_text_non_ascii` added; `test_rust_span.py` renamed to `test_unicode_codepoint_indices` asserting codepoint slice.
Assessment: fix addresses the named consequence at the named lines; non-ASCII regression pinned. Accept.

### errhandling-1 — Fixed
Claim: `_span_text` silently falls back to `terminals[span.start:span.end]` (codepoint slice) when `span.text()` returns None on a source-bearing span — silent wrong text, no diagnostic.
Diff at `fltk2gsm.py:34-39`: guard added — if `hasattr(span,"has_source")` and `span.has_source()`, raise `ValueError` instead of falling back. Fallback now reached only for genuinely sourceless spans.
Assessment: guard closes the silent-wrong-text path; consequence neutralized. Accept.

### errhandling-2 — Fixed
Claim: same pattern in `extract_span_text` (`unparse/pyrt.py`).
Diff at `pyrt.py:46-49`: identical `has_source()` guard raising `ValueError`.
Assessment: Accept.

### errhandling-3 — Won't-Do
Claim: sourceless fall-through in span getter/`to_pyobject` logs nothing; caller cannot distinguish "always sourceless" from "source dropped." Consequence: observability gap in on-call traces.
Rationale: after correctness-1, sourced spans return correct text; the None branch is now reached only for genuinely-sourceless spans (the expected common case); debug logging in a hot accessor would pollute traces for the normal path, and the logger-name/level choice is an unmade infra decision.
Assessment: the finding's stated consequence is an observability *nicety*, not active harm — it never claims a wrong result or a missed failure, only reduced trace legibility for an expected branch. Debug-logging the common, correct case in a per-node hot accessor is a defensible decline; the responder's premise (sourceless = expected) is correct given correctness-1. Won't-Do rationale clears the bar. Accept.

### errhandling-4 — Won't-Do
Claim: the finding text itself states "No change required. Confirmed correct" — the `expect` panics only on a genuine loop-invariant violation, with the expected bad-input case already handled by the preceding `count != 1 → PyValueError` return.
Assessment: reviewer raised no defect; nothing to do. Accept.

### errhandling-5 — Fixed
Claim: `downcast_unchecked` SAFETY comment should state the consequence of violating the single-rlib invariant: memory corruption, not merely a wrong result.
Diff in `gsm2tree_rs.py` preamble emission: comment now reads "...causing memory corruption (out-of-bounds Arc pointer deref, type confusion)".
Assessment: comment now states the severity at the named site. Accept.

### errhandling-6 — Fixed
Claim: `py.import("fltk._native")` failure surfaces a bare ImportError with no context tying it to span-source preservation.
Diff: wrapped in `PyRuntimeError::new_err("span source preservation requires fltk._native (SourceText): {e}")`.
Assessment: context added as requested. Accept.

### security-1 — Fixed (via errhandling-5)
Claim: `downcast_unchecked` soundness rests on an unenforced cross-cdylib single-rlib invariant; layout skew → UB (the reviewer also proposed a checked downcast / ABI-version guard).
Disposition: SAFETY comment expanded with the memory-corruption consequence; `downcast_unchecked` retained.
Assessment: the reviewer's own suggested-fix concedes a checked `downcast` "also fails cross-cdylib (distinct type objects)" — the responder is correct that the checked path is not a real alternative under the shared-rlib design; the unchecked downcast guarded by `is_instance` is the sanctioned pattern. The ABI-version-guard hardening is a larger design item, not in this finding's required remediation. Documenting the UB severity is the proportionate response to a build-graph-controlled (non-runtime-input) threat. Accept.

### test-1 — Fixed
Claim: no test directly asserts `isinstance(node.span, fltk._native.Span)` + `span.text()` after a live Rust-backend parse; node-level span source-preservation only verified indirectly.
Diff: `test_phase4_rust_fixture.py` adds `test_rust_backend_node_span_is_native_and_text_works` (isinstance + `text() is not None`) and `test_rust_backend_node_span_text_non_ascii` (non-ASCII guard) to `TestAC7BothBackends`.
Assessment: both gaps named in the finding now have direct tests. Accept.

### test-2 — Fixed
Claim: §4-item-8 pyright fixtures use `typing.cast` everywhere, so they never falsify whether a bare uncast `accept_fn(node.span)` call site fails pyright after the union widening — the backward-compat claim is untested at the call-site level.
Diff: `test_cst_protocol.py` adds `_PYTHON_BACKEND_UNCASTED_CALLSITE_FIXTURE` + `test_python_backend_uncasted_callsite_annotation_churn`, asserting a bare call site requires `type: ignore[arg-type]` and that the suppressor is load-bearing (zero pyright errors with it).
Assessment: the test now documents the true scope of the backward-compat guarantee (cast/annotated call sites only); the annotation-churn consequence for bare uncast sites is made explicit rather than hidden. This is the honest disposition of the finding, not a paper-over. Accept.

### reuse-1 / quality-1 — Fixed
Claim: `text_str` is dead duplicate of `text()` (divergence risk); `source_as_py` is dead public API that will confuse the source-preservation strategy.
Diff: `text_str` removed (`span.rs` no longer defines it — confirmed). `source_as_py` retained with an explicit doc comment explaining the cross-cdylib reason it cannot be used in generated code yet, plus the `TODO(span-source-as-py-crosscdylib)` reference.
Assessment: dead duplicate gone; retained primitive is the documented O(1) target for efficiency-deep-1's fix, with the constraint spelled out. Accept.

### reuse-2 — Fixed (via reuse-1)
`text_str` removed; `text()` is the single implementation. Divergence risk eliminated. Accept.

### quality-2 — Fixed
Claim: stale comment "source_as_py requires py token" points to the abandoned approach.
Diff at `gsm2tree_rs.py`: comment replaced with "py is always needed when has_span because get_source_text_type(py) is called in the source-bearing branch."
Assessment: comment now accurate. Accept.

### quality-3 — Won't-Do
Claim: `_span_text` terminals fallback is dead code post-regen and should be removed (or a removal-trigger TODO added).
Rationale: the fallback is still reachable for any in-flight bootstrap path combining a pre-regen sourceless parser with the new `fltk2gsm`; removing live fallback code is an active-harm risk, and the errhandling-1 guard already makes the fallback safe-or-raises (no silent wrong text). Removal is a follow-on once bootstrap closure is confirmed.
Assessment: the reviewer's premise ("dead code") is not established — the responder identifies a live bootstrap path, and the errhandling-1 guard neutralizes the finding's actual harm (silent wrong text). Removing reachable fallback to satisfy a tidiness finding would be the riskier move. Rationale argues concrete harm-of-removal and the safety guard is verified in `fltk2gsm.py:34-39`. Won't-Do sound. Accept.

### quality-6 — Fixed
Claim: `children_native()` returns `&Vec<(...)>` (non-idiomatic, `clippy::ptr_arg`, couples downstream to concrete container).
Diff: generator emits `pub fn children_native(&self) -> &[(label, enum)]` with body `self.children.as_slice()`. All four `*.rs` regenerated — confirmed zero remaining `&Vec` `children_native` returns across `src/` and both fixture crates.
Assessment: source-compatible change (Vec→&[T] via Deref), regen propagated. Accept.

## Disputed items

- **quality-4 / TODO(span-make-span-expr-registry)** — Need one of: (a) **do it now** — derive the Span class path in `_make_span_expr` (`gsm2parser.py:262`) from the registered `self.TerminalSpanType` or a hoisted class constant, eliminating the hardcoded string; OR (b) if the responder still maintains it should defer, **actually create the TODO** (a `TODO.md` entry AND a `TODO(span-make-span-expr-registry)` code comment at `gsm2parser.py:262`) AND justify why the registry-derivation is not a mechanical do-now. The rubric reading is (a): Q2 fails (mechanical, single-file, in-scope), so the correct outcome is do-now, not defer. The current state — a TODO disposition with no TODO recorded in either piece of the two-piece system — is not acceptable regardless.

## Approved

18 of 19 dispositions acceptable: 11 Fixed verified (correctness-1, errhandling-1/2/5/6, security-1, test-1/2, reuse-1/2 via quality-1, quality-2/6), 3 Won't-Do sound (errhandling-3/4, quality-3), 2 TODOs acceptable (gencode-poc-fltkg, span-source-as-py-crosscdylib). Not re-walked beyond the per-item evidence above.

---

## Verdict: REWORK

One disposition wrong: quality-4. The disposition claims `TODO(span-make-span-expr-registry)` but (1) no TODO exists in either `TODO.md` or code — a phantom defer — and (2) the rubric fails Q2 (the registry-derivation fix is mechanical, single-file, in-scope), so the correct outcome is do-it-now, not defer. Round 1 → REWORK.
