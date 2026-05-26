# Dispositions: Design Review — Phase 1 Span Rust Implementation

Concise. Precise. No padding. Audience: smart human/LLM.

---

design-1:
- Disposition: Fixed
- Action: Design already addresses this at design.md:195 — explicit statement that each `text()` call allocates a new `String` on the Rust side and `str` on the Python side, that the zero-copy constraint applies to Rust-internal representation only, and that this is bounded by the PyO3 FFI. No further edit needed.
- Severity assessment: Low. The reviewer is correct that silent omission would mislead implementers, but the design text already contains the exact clarification the reviewer requests.

design-2:
- Disposition: Fixed
- Action: Design already addresses this at design.md:179-193 — full `char_slice` implementation specified with signature `fn char_slice(src: &str, char_start: usize, char_end: usize) -> Option<&str>`, byte-offset table via `char_indices()`, sentinel for past-end, and bounds check against char count. The ASCII fast path's `end > src.len()` validity note is at design.md:179. No further edit needed.
- Severity assessment: Medium if unaddressed. The char-to-byte conversion is the hardest correctness point. The design specifies it fully.

design-3:
- Disposition: Fixed
- Action: Design already addresses this at design.md:96 — "Phase 1 scope note" paragraph explicitly states Phase 1 delivers capability and synthetic-node path only; no production parse path emits source-bearing spans; wiring the parser is a follow-up phase. No further edit needed.
- Severity assessment: Medium if unaddressed. User could approve believing Phase 1 delivers source-on-parsed-nodes. The explicit scope note prevents this.

design-4:
- Disposition: Fixed
- Action: Design already addresses this at design.md:128 — file changes table entry for `src/span.rs` reads "all in one module so private-field access works". No further edit needed.
- Severity assessment: Low. Compile error would catch any module split immediately.

design-5:
- Disposition: Fixed
- Action: Design already addresses this at design.md:287 — test #2 now reads `Span(1, 2).__eq__("not a span") is NotImplemented`, which directly tests the `NotImplemented` return rather than relying on `!=` operator fallback. No further edit needed.
- Severity assessment: Low. Behavior is correct via PyO3 derive; this is a test-coverage gap fix.

design-6:
- Disposition: Won't-Do
- Action: None — reviewer explicitly states "No finding" (notes line 142-144). This entry is a verification of a design claim, not a requested change. Marking Won't-Do because there is nothing to do.
- Rationale: Reviewer's own text: "No finding — confirming the design's claim (design.md:119) is correct." No action exists to take.

design-7:
- Disposition: Fixed
- Action: Design already addresses this at design.md:311-313 — the open question is moved to a "Decided (not open)" section with the classmethod choice and rationale. No further edit needed.
- Severity assessment: Low. Cosmetic inconsistency that could confuse an implementer scanning open questions.
