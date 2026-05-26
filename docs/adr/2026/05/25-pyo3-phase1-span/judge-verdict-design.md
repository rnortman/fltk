# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/05/25-pyo3-phase1-span/design.md`. Round 1.
Notes: 1 reviewer file; 7 findings.

## Other findings walk

### design-1 — Fixed
Claim: `text()` returns `Option<String>` (two allocations per access), contradicting the memory-efficiency constraint; design should acknowledge the per-access copy.
Disposition: Fixed — already addressed in design.
Verification: design.md:195 explicitly states "each `text()` call allocates a new `String` on the Rust side and a new `str` on the Python side — the zero-copy constraint applies to the Rust-internal representation only... not to the Python-facing retrieval path which is bounded by the PyO3 FFI." This is exactly the clarification the reviewer requested.
Assessment: Fix verified. Accept.

### design-2 — Fixed
Claim: `char_slice` helper used but never defined; hardest correctness point delegated to unspecified helper.
Disposition: Fixed — already addressed in design.
Verification: design.md:179-193 provides full `char_slice` implementation: signature `fn char_slice(src: &str, char_start: usize, char_end: usize) -> Option<&str>`, byte-offset table via `char_indices()`, past-end sentinel via `chain(once(src.len()))`, bounds check `char_end > byte_offsets.len() - 1`, and note that ASCII fast path's byte-len check is valid because byte len == char count for ASCII.
Assessment: Fix verified. Accept.

### design-3 — Fixed
Claim: Phase 1 never attaches source on the parse path; "better API" unreachable from real CSTs; design should say so explicitly.
Disposition: Fixed — already addressed in design.
Verification: design.md:96 reads "Phase 1 delivers the *capability* for source-bearing spans and validates it via synthetic construction... No production parse path emits source-bearing spans in this phase — all `Span` objects from `TerminalSource.consume_*` and `fltk_parser.py` remain sourceless. Wiring the parser to attach `SourceText` to emitted spans is a follow-up phase."
Assessment: Fix verified. Accept.

### design-4 — Fixed
Claim: `SourceInner` is `pub(crate)` with private fields, `with_source` reads `source.inner` — design should state single-module assumption.
Disposition: Fixed — already addressed in design.
Verification: design.md:128 file-changes table entry for `src/span.rs` reads "all in one module so private-field access works."
Assessment: Fix verified. Accept.

### design-5 — Fixed
Claim: Test #2 (`!=` operator) cannot distinguish `False` from `NotImplemented`; does not test the requirement.
Disposition: Fixed — already addressed in design.
Verification: design.md:287 now reads `Span(1, 2).__eq__("not a span") is NotImplemented`, which directly tests the `NotImplemented` return.
Assessment: Fix verified. Accept.

### design-6 — Won't-Do
Claim: Reviewer's own text: "No finding — confirming the design's claim is correct."
Rationale: No action to take; reviewer explicitly marked this as verification, not a finding.
Assessment: Won't-Do correct. Accept.

### design-7 — Fixed
Claim: Open Question #2 left unresolved despite the design body already committing to `with_source` classmethod throughout.
Disposition: Fixed — already addressed in design.
Verification: design.md:311-313 moves the question to a "Decided (not open)" section with classmethod choice and rationale.
Assessment: Fix verified. Accept.

## Approved

7 findings: 6 Fixed verified, 1 Won't-Do sound.

---

## Verdict: APPROVED
