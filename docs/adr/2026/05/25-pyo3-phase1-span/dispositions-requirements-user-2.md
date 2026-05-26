# Dispositions: User Requirements Notes Round 2

---

user-2-1 (memory efficiency and zero-copy in Rust):
- Disposition: Fixed
- Action: Added "Memory efficiency (Rust)" constraint requiring memory-efficient, ideally zero-copy source text holding and retrieval in Rust. Section: Constraints.
- Severity assessment: Without this constraint, an implementation could naively copy source text per span, defeating the purpose of the Rust backend.

user-2-2 (acceptable inefficiency in Python, prefer non-copying):
- Disposition: Fixed
- Action: Added "Memory efficiency (Python)" constraint stating Python path may be less efficient but should ideally use non-copying slicing of immutable data. Section: Constraints.
- Severity assessment: Sets expectations for cross-boundary cost without over-constraining the PyO3 interface.

user-2-3 (UTF-8-only backing acceptable):
- Disposition: Fixed
- Action: Added "Source backing" constraint scoping Rust backend to UTF-8 text only, explicitly dropping the Python implementation's nominal support for other backings. Section: Constraints.
- Severity assessment: Eliminates a category of design complexity that has no real-world use.

user-2-4 (mmap nice-to-have, not required):
- Disposition: Fixed
- Action: Added "mmap" constraint noting file-backed source via mmap is ideal but not required. Section: Constraints.
- Severity assessment: Prevents over-engineering while preserving future option.
