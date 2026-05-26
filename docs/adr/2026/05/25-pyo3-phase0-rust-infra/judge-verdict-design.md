# Judge verdict — design review

Phase: design. Design doc: `design.md`. Round 1.
Notes: 1 reviewer file; 6 findings.

## Other findings walk

### design-1 — Fixed
Claim: `#[pymodule] fn fltk_native` produces `PyInit_fltk_native` but Python imports `fltk._native` expecting `PyInit__native`; consequence is ImportError at runtime (sole acceptance criterion fails).
Evidence: design.md:70 now reads `fn _native(m: &Bound<'_, PyModule>)`. Lines 53-54 explain the naming constraint.
Assessment: fix addresses the exact issue. Accept.

### design-2 — Fixed
Claim: switching build-backend to maturin breaks all CI (lint, typecheck, test) because `uv run` invokes maturin which requires Rust, absent from ci.yml.
Evidence: design.md:113-125 adds "CI changes" subsection with `dtolnay/rust-toolchain@stable` and `maturin develop` steps. Line 228 adds ci.yml to file summary. Lines 241-243 update edge-case text to state Rust is required for all `uv run`.
Assessment: fix addresses the consequence (CI breakage) with the standard action (install Rust in CI). Accept.

### design-3 — Fixed
Claim: pyright may fail on `from fltk._native import ...` because no stub exists; consequence is `make check` failure.
Evidence: design.md:217 adds "Pyright compatibility" paragraph explaining `importorskip` returns `Any` (no type error expected) and prescribes fallback (`# type: ignore` or exclude) if pyright does complain.
Assessment: acknowledges the risk, explains why it is unlikely, and provides contingency. Sufficient for a design doc. Accept.

### design-4 — Fixed
Claim: baseline test checks only class names + label enums, missing the primary regression surface (method/child-type drift).
Evidence: design.md:187-195 adds a third comparison surface — public method names per class — with assertion and updated prose (line 195) describing what each surface catches.
Assessment: method-name comparison catches the child-access API drift the reviewer identified. Accept.

### design-5 — Fixed
Claim: `python-source = "."` diverges from exploration's `python-packages = ["fltk"]` and risks packaging stray directories.
Evidence: design.md:90 now reads `python-packages = ["fltk"]`. Line 95 explains the explicit-package rationale.
Assessment: matches exploration recommendation; eliminates auto-discovery footgun. Accept.

### design-6 — Fixed
Claim: `extension-module` declared in both Cargo.toml and `[tool.maturin]`; breaks future `cargo test`.
Evidence: design.md:46-49 — Cargo.toml `[dependencies]` section shows `pyo3 = { version = "0.23" }` with no features. Line 49 explains the single-declaration rationale.
Assessment: extension-module now declared only in `[tool.maturin]` per maturin convention. Accept.

## Approved

6 findings: 6 Fixed verified.

---

## Verdict: APPROVED
