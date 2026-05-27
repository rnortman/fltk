# Judge verdict — deep review

Phase: deep (design phase). Design: `design.md`. Base 0f9b786..HEAD 33d6704. Round 1.
Notes: 7 reviewer files; 22 findings (3 errhandling, 0 correctness, 0 security, 6 test, 4 reuse, 2 quality, 4 efficiency — with quality-1/efficiency-2 merged, net 19 distinct).

## Added TODOs walk

### errhandling-1 — TODO(cst-unwrap-diagnostic) at cst_poc.rs:4-6
Q1 (worth doing): yes — the `found.unwrap()` is safe today but a broken invariant in a future refactor produces a zero-context panic; making it diagnostic is real value.
Q2 (design/owner input required): no — the fix is mechanical: replace `.unwrap()` with `.expect("invariant: ...")` across ~5 call sites, or refactor to early-return. No design decisions involved; both approaches are spelled out in the finding and the TODO itself.
Furthermore: this code was introduced in this iteration, so the deferral creates a latent problem this iteration created.
Assessment: Q2 fails. The fix is 5 one-line substitutions (or a small refactor the TODO itself describes). No design cycle needed. **Do-now.**

### errhandling-2 — TODO(cst-constructor-import-context) at cst_poc.rs:7-9
Q1 (worth doing): yes — an `ImportError` from inside a constructor with no context is confusing.
Q2 (design/owner input required): yes — this overlaps with `cst-unknown-span-cache` (which eliminates the import entirely); fixing just the error wrapping now would be throwaway work once the caching design lands. The caching approach itself requires a decision about `GILOnceCell` lifetime, whether to cache at module-init or lazily, and interaction with `lib.rs` registration order. Reasonable to defer.
Assessment: TODO acceptable.

### errhandling-3 — TODO(cst-downcast-context) at cst_poc.rs:13-15
Q1 (worth doing): yes — bare downcast errors from corrupted children lists are non-diagnostic.
Q2 (design/owner input required): no — the fix is mechanical: wrap each `downcast::<PyTuple>()?` with a `.map_err(...)` adding node type, method name, and index. No design decisions. The pattern is clear from the finding.
Furthermore: this code was introduced in this iteration.
Assessment: Q2 fails. Mechanical wrapping, no design cycle. **Do-now.**

### efficiency-1 — TODO(cst-unknown-span-cache) at cst_poc.rs:10-12
Q1 (worth doing): yes — per-node `py.import` + `getattr` on construction hot path; Phase 3 inherits.
Q2 (design/owner input required): yes — `GILOnceCell` vs module-init caching, interaction with `lib.rs` registration, and whether the cached handle should be `Py<Span>` or `PyObject` are all design calls that affect the module's initialization contract. The design doc explicitly punted this ("construction is not on any hot path in Phase 2").
Assessment: TODO acceptable.

### efficiency-3 — TODO(cst-accessor-early-exit) at cst_poc.rs:16-18
Q1 (worth doing): yes — avoids full O(n) scan when error is known at count==2.
Q2 (design/owner input required): no — the change is mechanical: add `if count >= 2 { break; }` after the increment, change error message to "at least 2." No design decision.
Furthermore: this code was introduced in this iteration.
Assessment: Q2 fails. Mechanical optimization, no design cycle. **Do-now.**

### reuse-1 — TODO(rust-cst-macro) covering filter loop duplication
Q1 (worth doing): yes — 10 loop copies; Phase 3 multiplies by N node types.
Q2 (design/owner input required): yes — proc-macro vs code-generation template vs generic helper is a design decision that shapes Phase 3 architecture. The design doc explicitly scopes this as "pending macro extraction."
Assessment: TODO acceptable.

### reuse-2 — TODO(rust-cst-macro) covering constructor body duplication
Q1 (worth doing): yes — N-copy constructor body in Phase 3.
Q2 (design/owner input required): yes — same macro/generation design as reuse-1.
Assessment: TODO acceptable.

### reuse-3 — TODO(rust-cst-macro) covering `__eq__`/`__hash__`/`__repr__` duplication
Q1 (worth doing): yes — same as reuse-1/2.
Q2 (design/owner input required): yes — same macro/generation design.
Assessment: TODO acceptable.

### reuse-4 — TODO(cst-generator-vs-list) at cst_poc.rs:19-21
Q1 (worth doing): yes — list vs iterator divergence from Python counterpart will break call sites at integration.
Q2 (design/owner input required): yes — whether to return list or iterator (or accept both) is a cross-language API contract decision that affects all consumers. Design doc explicitly calls this "deliberate simplification" requiring Phase 3 resolution.
Assessment: TODO acceptable.

### quality-2 — TODO(rust-cst-macro) covering child/maybe loop duplication
Q1 (worth doing): yes — 10 body-copies within this file.
Q2 (design/owner input required): yes — same macro/generation design scope as reuse-1.
Assessment: TODO acceptable.

## Other findings walk

### correctness — no findings
Reviewer explicitly confirmed no defects. No action needed.

### security — no findings
No trust boundary crossed; standalone PoC. No action needed.

### test-1 — Fixed
Claim: `child_name()` return type not asserted to be non-tuple; a future refactor changing it to return the tuple would pass silently.
Diff at `test_rust_cst_poc.py:91`: added `assert not isinstance(result, tuple)` in `test_append_name_and_child_name`.
Assessment: fix addresses the consequence at the named location. Accept.

### test-2 — Fixed
Claim: no test verifies `children_item()` filters by label (cross-label exclusion for Items).
Diff at `test_rust_cst_poc.py:377-391`: added `test_cross_label_filtering` — appends ITEM, NO_WS, ITEM, WS_ALLOWED children and asserts each `children_*` returns only its own label's children, plus `children_ws_required()` returns empty.
Assessment: fix addresses the consequence directly. Accept.

### test-3 — Won't-Do
Claim: reviewer self-corrected — `tup == (Identifier.Label.NAME, s)` already covers tuple structure via Python equality.
Rationale: "The reviewer found no defect and withdrew the finding."
Inspection: reviewer's own notes state "This is fine — the two behaviors are intentionally different" and "No bug here" and conclude "the assertion is adequate" after analysis.
Assessment: finding was withdrawn by the reviewer; Won't-Do is the correct disposition. Accept.

### test-4 — Fixed
Claim: `Identifier.Label.NAME != None` not directly tested; PyO3 cross-type `__richcmp__` fallback is load-bearing.
Diff at `test_rust_cst_poc.py:39-43`: added `test_label_not_equal_none` with `assert Identifier.Label.NAME != None` and `assert (Identifier.Label.NAME == None) is False`.
Assessment: fix addresses the consequence. Accept.

### test-5 — Fixed
Claim: no test for cross-type `__eq__` (`Identifier != Items`, `Identifier != "string"`, etc.).
Diff at `test_rust_cst_poc.py:255-263`: added `test_not_equal_cross_type` asserting `ident != items`, `!= "string"`, `!= None`, `!= 42`.
Assessment: fix addresses the consequence. Accept.

### test-6 — Fixed
Claim: no test for keyword-only `span=` construction storing the provided span.
Diff at `test_rust_cst_poc.py:220-226`: added `test_span_keyword_construction_stores_provided_span` asserting `node.span == s` and `node.span is not UnknownSpan`.
Assessment: fix addresses the consequence. Accept.

### quality-1 / efficiency-2 — Fixed
Claim: `into_pyobject(py)` called inside the loop in all five `extend_<label>` methods; N label allocations per extend instead of 1.
Diff: all six `extend_*` methods (`extend_name` at line 158, `extend_item` at 328, `extend_no_ws` at 400, `extend_ws_allowed` at 471, `extend_ws_required` at 543) now hoist `let label = ...into_pyobject(py)?.into_any().unbind()` before the loop and use `label.bind(py).clone()` per iteration.
Assessment: fix addresses the consequence. Template bug eliminated; Phase 3 generator inherits the correct pattern. Accept.

### efficiency-4 — Won't-Do
Claim: reviewer noted `__eq__` delegation to Python `==` is "not a defect" and "no change needed."
Rationale: "Reviewer noted this as 'not a defect' and explicitly requested no action."
Inspection: reviewer's own notes say "No change needed; flagged so a reader doesn't 'optimize' it."
Assessment: reviewer self-identified as informational-only. Won't-Do correct. Accept.

## Disputed items

- **errhandling-1 / TODO(cst-unwrap-diagnostic)**: Q2 fails — `.unwrap()` -> `.expect("...")` is a 1-line substitution per call site, no design input needed. This iteration introduced the code. Disposition should be Fixed.
- **errhandling-3 / TODO(cst-downcast-context)**: Q2 fails — `.map_err(|e| PyTypeError::new_err(...))` wrapping is mechanical. This iteration introduced the code. Disposition should be Fixed.
- **efficiency-3 / TODO(cst-accessor-early-exit)**: Q2 fails — `if count >= 2 { break; }` is a 2-line addition per method, no design decision. This iteration introduced the code. Disposition should be Fixed.

## Approved

16 dispositions accepted: 6 Fixed verified, 2 Won't-Do sound, 7 TODOs acceptable (cst-constructor-import-context, cst-unknown-span-cache, rust-cst-macro x4, cst-generator-vs-list), 1 no-findings-no-action (correctness/security combined).

---

## Verdict: REWORK

Three TODO dispositions fail Q2 (mechanical fixes, no design cycle required, all on code this iteration introduced): errhandling-1/cst-unwrap-diagnostic, errhandling-3/cst-downcast-context, efficiency-3/cst-accessor-early-exit. Round 1.
