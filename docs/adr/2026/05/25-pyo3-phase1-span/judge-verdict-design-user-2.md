# Judge verdict — design review (user notes round 2)

Phase: design. Doc: `docs/adr/2026/05/25-pyo3-phase1-span/design.md`. Round 2.
Notes: `notes-design-user-2.md`; 4 findings (user-2-a through user-2-d).

## Findings walk

### user-2-a — Fixed (is_ascii / O(N) eliminated)
Claim: `is_ascii` optimization badly reasoned; O(N) codepoint-to-byte path unacceptable.
Disposition: Fixed.
Evidence: `SourceInner` (design lines 145-147) contains only `text: String` — no `is_ascii` field. Rust `text()` (lines 363-378) performs direct byte-range slicing with `is_char_boundary` safety check; no character-index conversion exists anywhere in the design. No `char_slice` helper present.
Assessment: Fully addressed. Accept.

### user-2-b — Fixed (abstract index contract)
Claim: Drop codepoint-index guarantee; make indices abstract; access methods are the contract.
Disposition: Fixed.
Evidence: "Index Semantics — Abstract Indices" section (lines 232-252) defines: Python = codepoints, Rust = bytes, access methods are the contract. `SpanProtocol` (lines 43-50) exposes only `text()`, `text_or_raise()`, `has_source()`, `len()`, `is_empty()`, `merge()`, `intersect()` — no `start`/`end` properties. Existing consumers documented (lines 245-252) as Python-backend-only and acknowledged as future migration targets.
Assessment: Fully addressed. Accept.

### user-2-c — Fixed (private Rust fields)
Claim: Make start/end private in Rust; force access through methods.
Disposition: Fixed.
Evidence: Rust struct (lines 153-158) has no `#[pyo3(get)]` on `start`/`end`. API Surface section (line 195): "NO attribute access." Rust test 5 (line 521): verifies `span.start` raises `AttributeError`. `repr` still shows indices for debugging (line 208).
Assessment: Fully addressed. Accept.

### user-2-d — Fixed (utility methods)
Claim: Add `len()`, `is_empty()`, `merge()`, `intersect()`.
Disposition: Fixed.
Evidence: "Utility Methods" section (lines 254-311) provides full specification and Rust implementations for all four. Python `Span` dataclass (lines 94-114) implements all four. `SpanProtocol` (lines 48-50) includes all four. Tests 17-20 in both `test_span.py` and `test_rust_span.py` cover them. Edge case for merge/intersect with sentinel spans documented (lines 477).
Assessment: Fully addressed. Accept.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED
