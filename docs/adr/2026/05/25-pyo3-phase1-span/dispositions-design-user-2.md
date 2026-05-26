# Dispositions: User Notes Round 2

Source: `notes-design-user-2.md`

---

user-2-a (is_ascii reasoning flawed):
- Disposition: Fixed
- Action: Removed `is_ascii` field from `SourceInner`, removed `char_slice` helper, removed O(N) codepoint-to-byte conversion path. Rust `text()` now does direct byte-range slicing with `is_char_boundary` safety check. Sections: "Rust Struct Layout", "Rust Implementation Details > text method", "SourceText Struct".
- Severity assessment: The is_ascii optimization was premised on ASCII being the common case, but UTF-8 source text is universal in practice. The O(N) fallback would have been the default path for any non-ASCII source, making text() unexpectedly slow.

user-2-b (drop codepoint-index guarantee, make indices abstract):
- Disposition: Fixed
- Action: Added "Index Semantics -- Abstract Indices" section defining the new contract: indices are opaque (codepoints in Python, bytes in Rust), access methods are the contract. Updated SpanProtocol to omit `start`/`end` properties. Updated Rust struct to remove `#[pyo3(get)]` on `start`/`end`. Documented all existing consumers of `terminals[span.start:span.end]` and noted they remain valid on the Python backend. Updated "Decided (not open)" section.
- Severity assessment: Central design decision. Eliminates the impedance mismatch between Python str codepoint indexing and Rust UTF-8 byte indexing. Without this, every Rust text() call would require O(N) index translation.

user-2-c (make start/end private in Rust, force everything through access methods):
- Disposition: Fixed
- Action: Removed `#[pyo3(get)]` from `start` and `end` in the Rust `Span` struct. Updated Rust Python API Surface section to document no attribute access. Updated Rust test plan (test 5) to verify `span.start` raises `AttributeError`. repr still shows raw indices for debugging.
- Severity assessment: Enforces the abstract-index contract at the API level for the Rust backend. Prevents Rust-backend consumers from writing non-portable code that assumes index semantics.

user-2-d (add len(), is_empty(), merge(), intersect() utility methods):
- Disposition: Fixed
- Action: Added "Utility Methods" section with full specification and Rust implementations for all four methods. Added methods to Python `Span` dataclass. Added methods to `SpanProtocol`. Added test cases 17-20 in both `test_span.py` and `test_rust_span.py`. Added edge case for merge/intersect with sentinel spans. Updated File Changes table.
- Severity assessment: Without these methods, users needing span length or combining spans would be forced to access raw indices, defeating the abstract-index contract.
