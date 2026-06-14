## reuse-1

**File:line**: `fltk/fegen/genparser.py:400` and `fltk/fegen/gsm2lib_rs.py:16`

**What's duplicated**: `_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")` is defined identically in both files. `genparser.py` adds it at line 400 (new in this diff) for the `gen_rust_lib` CLI validation; `gsm2lib_rs.py` defines the same pattern at line 16 for the generator-level validation in `_validate_rust_ident`.

**Existing function/utility**: `gsm2lib_rs._RUST_IDENT_RE` (line 16) and `gsm2lib_rs._validate_rust_ident` (line 19–23). The CLI command `gen_rust_lib` already calls `gsm2lib_rs.LibSpec.standard(module_name, ...)`, which internally calls `spec.validate()` → `_validate_rust_ident`. The CLI's own pre-check at `genparser.py:434` (`if not module_name or not _RUST_IDENT_RE.match(module_name)`) therefore duplicates a validation that the generator layer already performs. The module-level regex in `genparser.py` could be removed; the CLI could simply catch the `ValueError` that `RustLibGenerator.__init__` raises via `spec.validate()`, matching the existing error-handling shape already present in `gen_rust_lib` at lines 144–148.

**Consequence**: Two regex constants with identical patterns must be kept in sync if the definition of "valid Rust identifier" ever changes (e.g., to accept raw identifiers or Unicode). The CLI currently raises on the pre-check before the generator raises, so if the generator's validation were tightened, the CLI's guard would silently fall behind. As the code stands the pre-check is also slightly inconsistent: it tests `not module_name or not _RUST_IDENT_RE.match(module_name)` whereas `_validate_rust_ident` tests `not value or not _RUST_IDENT_RE.match(value)` — same logic but duplicated — while `gen_rust_native_lib` has no pre-check at all and relies solely on the generator raising `ValueError` (lines 172–178), which is already the correct pattern.

---

No other findings.
